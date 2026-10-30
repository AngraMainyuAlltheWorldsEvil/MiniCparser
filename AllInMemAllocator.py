from Lib import RiscV
from Lib.Operands import Temporary, Operand, S
from Lib.Statement import Instruction
from Lib.Allocator import Allocator
from typing import List


class AllInMemAllocator(Allocator):
        #il y a une fonction qui retourne les emplacements libre sur la pile
        
    def replace(self, old_instr: Instruction) -> List[Instruction]:
        """Replace Temporary operands with the corresponding allocated
        memory location."""
        numreg = 1
        dest=True
        before: List[Instruction] = []
        after: List[Instruction] = []
        new_args: List[Operand] = []
        for arg in old_instr.args():
            print(old_instr)
          #  print(old_instr.is_read_only())
            if(isinstance(arg,Temporary)):
                loc = arg.get_alloced_loc()
                reg = S[numreg]
                numreg+=1
                if((old_instr.is_read_only()) or ( not dest)):#si c est une instruction 
                    before.append(RiscV.ld(reg, loc))
                else:
                    if dest == True: #si c est un write le 1er argument est le registre de destination et faut donc enregistrer le resultat
                        after.append(RiscV.sd(reg, loc))
                        dest=False
                        
                    else:
                        before.append(RiscV.ld(reg, loc))
                
                new_args.append(reg)
                    
                
            else:
                new_args.append(arg)
            dest=False
           
        # TODO: compute before,after,args.
        # TODO: iterate over old_args, check which argument
        # TODO: is a temporary (e.g. isinstance(..., Temporary)),
        # TODO: and if so, generate ld/sd accordingly. Replace the
        # TODO: temporary with S[1], S[2] or S[3] physical registers.
        new_instr = old_instr.with_args(new_args)
        print(new_instr)
        return before + [new_instr] + after

    def prepare(self) -> None:
        """Allocate all temporaries to memory.
        Invariants:
        - Expanded instructions can use s2 and s3
          (to store the values of temporaries before the actual instruction).
        """
        self._fdata._pool.set_temp_allocation(
            {temp: self._fdata.fresh_offset()
             for temp in self._fdata._pool.get_all_temps()})
