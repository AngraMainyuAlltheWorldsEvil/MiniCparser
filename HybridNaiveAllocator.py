from Lib import RiscV
from Lib.Operands import GP_REGS, DataLocation, Offset, Temporary, Operand, S
from Lib.Statement import Instruction
from Lib.Allocator import Allocator
from typing import List, Dict


class HybridNaiveAllocator(Allocator):

    def replace(self, old_instr: Instruction) -> List[Instruction]:
        before: List[Instruction] = []
        after: List[Instruction] = []
        new_args: List[Operand] = []
        numreg = 1

        args = old_instr.args()
        for i, arg in enumerate(args):
            if isinstance(arg, Temporary):
                loc = arg.get_alloced_loc()
                if isinstance(loc, Offset):
                    reg = S[numreg]
                    numreg += 1
                    is_dest = (i == 0) and not old_instr.is_read_only()
                    if is_dest:
                        after.append(RiscV.sd(reg, loc))
                    else:
                        before.append(RiscV.ld(reg, loc))
                    new_args.append(reg)
                else:
                    new_args.append(loc)
            else:
                new_args.append(arg)

        instr = old_instr.with_args(new_args)
        return before + [instr] + after

    def prepare(self) -> None:
        """Allocate all temporaries to registers first (like Naive), and then
        memory (like AllInMem).
        Invariants: - Expanded instructions can use s1, s2 and s3
          (to store the values of temporaries before the actual instruction).
        """
        regs = list(GP_REGS)  # Get a writable copy
        temp_allocation: Dict[Temporary, DataLocation] = dict()
        for tmp in self._fdata._pool.get_all_temps():
            if regs:
                location = regs.pop()
            else:
                location = self._fdata.fresh_offset()
            temp_allocation[tmp] = location
        self._fdata._pool.set_temp_allocation(temp_allocation)
