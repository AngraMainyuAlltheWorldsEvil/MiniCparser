from typing import Callable, List
from MiniCVisitor import MiniCVisitor
from MiniCParser import MiniCParser
from Lib.LinearCode import CodeStatement, LinearCode
from Lib import RiscV
from Lib.RiscV import Condition
from Lib import Operands
from antlr4.tree.Trees import Trees
from Lib.Errors import MiniCInternalError, MiniCUnsupportedError

"""
CAP, MIF08, three-address code generation + simple alloc
This visitor constructs an object of type "LinearCode".
"""


class MiniCCodeGen3AVisitor(MiniCVisitor):

    _current_function: LinearCode
    # Shortcuts for methods of member objects
    fresh_tmp: Callable[[], Operands.Temporary]
    fresh_label: Callable[[str], RiscV.Label]
    add_statement: Callable[[CodeStatement], None]
    add_instruction_PRINTLN_INT: Callable[[Operands.DataLocation], None]
    add_comment: Callable[[str], None]
    get_label_div_by_zero: Callable[[], RiscV.Label]

    def __init__(self, debug, parser):
        super().__init__()
        self._parser = parser
        self._debug = debug
        self._functions = []
        self._lastlabel = ""
        self._continue_stack = []

    def get_functions(self) -> List[LinearCode]:
        return self._functions

    def printSymbolTable(self):  # pragma: no cover
        print("--variables to temporaries map--")
        for keys, values in self._symbol_table.items():
            print(keys + '-->' + str(values))

    # handle variable decl

    def visitVarDecl(self, ctx) -> None:
        type_str = ctx.typee().getText()
        vars_l = self.visit(ctx.id_l())
        for name in vars_l:
            if name in self._symbol_table:
                raise MiniCInternalError(
                    f"Variable {name} has already been declared")
            else:
                tmp = self.fresh_tmp()
                self._symbol_table[name] = tmp
                if type_str not in ("int", "bool"):
                    raise MiniCUnsupportedError(f"Unsupported type {type_str}")
                # Initialization to 0 or False, both represented with 0
                self.add_statement(
                    RiscV.li(tmp, Operands.Immediate(0)))

    def visitIdList(self, ctx) -> List[str]:
        t = self.visit(ctx.id_l())
        t.append(ctx.ID().getText())
        return t

    def visitIdListBase(self, ctx) -> List[str]:
        return [ctx.ID().getText()]

    # expressions

    def visitParExpr(self, ctx) -> Operands.Temporary:
        return self.visit(ctx.expr())

    def visitIntAtom(self, ctx) -> Operands.Temporary:
        val = Operands.Immediate(int(ctx.getText()))
        dest_temp = self.fresh_tmp()
        self.add_statement(RiscV.li(dest_temp, val))
        return dest_temp

    def visitFloatAtom(self, ctx) -> Operands.Temporary:
        raise MiniCUnsupportedError("float literal")

    def visitBooleanAtom(self, ctx) -> Operands.Temporary:
        # true is 1 false is 0
        text=ctx.getText()
        temp_return=self.fresh_tmp()
        if text=="true":
            val=Operands.Immediate(1)
            self.add_statement(RiscV.li(temp_return,val))
        
        if(text=="false"):
            val=Operands.Immediate(0)
            self.add_statement(RiscV.li(temp_return,val))
        return temp_return

    def visitIdAtom(self, ctx) -> Operands.Temporary:
        try:
            # get the temporary associated to id
            return self._symbol_table[ctx.getText()]
        except KeyError:  # pragma: no cover
            raise MiniCInternalError(
                f"Undefined variable {ctx.getText()}, this should have failed to typecheck."
            )

    def visitStringAtom(self, ctx) -> Operands.Temporary:
        raise MiniCUnsupportedError("string atom")

    # now visit expressions

    def visitAtomExpr(self, ctx) -> Operands.Temporary:
        return self.visit(ctx.atom())

    def visitAdditiveExpr(self, ctx) -> Operands.Temporary:
        assert ctx.myop is not None
        tmpl: Operands.Temporary = self.visit(ctx.expr(0))
        tmpr: Operands.Temporary = self.visit(ctx.expr(1))
        temp_return = self.fresh_tmp()
        if ctx.myop.type == MiniCParser.MINUS:
            self.add_statement(RiscV.sub(temp_return, tmpl, tmpr))
        else:
            self.add_statement(RiscV.add(temp_return, tmpl, tmpr))
        return temp_return
            
           

    def visitOrExpr(self, ctx) -> Operands.Temporary:
        dest_temp= self.fresh_tmp()
        left_temp : Operands.Temporary = self.visit(ctx.expr(0))
        right_temp : Operands.Temporary = self.visit(ctx.expr(1))
        self.add_statement(RiscV.lor(dest_temp,left_temp,right_temp))
        return dest_temp

    def visitAndExpr(self, ctx) -> Operands.Temporary:
        dest_temp= self.fresh_tmp()
        left_temp : Operands.Temporary = self.visit(ctx.expr(0))
        right_temp : Operands.Temporary = self.visit(ctx.expr(1))
        self.add_statement(RiscV.land(dest_temp,left_temp,right_temp))
        return dest_temp

    def visitEqualityExpr(self, ctx) -> Operands.Temporary:
        return self.visitRelationalExpr(ctx)

    def visitRelationalExpr(self, ctx) -> Operands.Temporary:
        assert ctx.myop is not None
        c = Condition(ctx.myop.type)
        if self._debug:
            print("relational expression:")
            print(Trees.toStringTree(ctx, [], self._parser))
            print("Condition:", c)
        left_temp:  Operands.Temporary   = self.visit(ctx.expr(0))
        right_temp:  Operands.Temporary   = self.visit(ctx.expr(1))
        result_temp = self.fresh_tmp()
        skip = self.fresh_label("onesquive")
        self.add_statement(RiscV.li(result_temp,Operands.Immediate(1)))
        self.add_statement(RiscV.conditional_jump(skip, left_temp, c, right_temp))
        #print(RiscV.conditional_jump(skip, left_temp, c, right_temp))
        self.add_statement(RiscV.li(result_temp,Operands.Immediate(0)))
        self.add_statement(skip)
        return result_temp
    
    def visitMultiplicativeExpr(self, ctx) -> Operands.Temporary:
        assert ctx.myop is not None
        tmpl: Operands.Temporary = self.visit(ctx.expr(0))
        tmpr: Operands.Temporary = self.visit(ctx.expr(1))
        div_by_zero_lbl = self.get_label_div_by_zero()

            
        

        #print(self.visit(ctx.expr(1)))
        temp_return = self.fresh_tmp()
        if(ctx.myop.type==MiniCParser.MULT):
            self.add_statement(RiscV.mul(temp_return,tmpl,tmpr))
        if(ctx.myop.type==MiniCParser.DIV):
            self.add_statement(RiscV.conditional_jump(div_by_zero_lbl, tmpr, Condition(MiniCParser.EQ), Operands.ZERO))
        #    self.add_statement(div_by_zero_lbl)
            self.add_statement(RiscV.div(temp_return,tmpl,tmpr))
        if(ctx.myop.type==MiniCParser.MOD):
            self.add_statement(RiscV.conditional_jump(div_by_zero_lbl, tmpr, Condition('beq'), Operands.ZERO))
         #   self.add_statement(div_by_zero_lbl)
            self.add_statement(RiscV.rem(temp_return,tmpl,tmpr))
        
        return temp_return  
    #faut faire avec 0 et 1 le not 
    def visitNotExpr(self, ctx) -> Operands.Temporary:
        val = self.visit(ctx.expr())
        dest_temp=self.fresh_tmp()
        l_true = self.fresh_label("pas_vrai")
        self.add_statement(RiscV.li(dest_temp,Operands.Immediate(1)))
        self.add_statement(RiscV.conditional_jump(l_true,val,Condition('beq'),Operands.ZERO))
        self.add_statement(l_true)
        return dest_temp

    def visitUnaryMinusExpr(self, ctx) -> Operands.Temporary:
        val = self.visit(ctx.expr())
        result = self.fresh_tmp()
        self.add_statement(RiscV.sub(result, Operands.ZERO, val))           # result = 0 - val
        return result
        
    def visitProgRule(self, ctx) -> None:
        self.visitChildren(ctx)

    def visitFuncDef(self, ctx) -> None:
        funcname = ctx.ID().getText()
        self._current_function = LinearCode(funcname)

        # Our code can deal with multiple functions, and each function is a
        # different LinearCode object. But don't bother the user with
        # self._current_function each time, define a few shortcuts to make the
        # code simpler. This comes here and not in __init__ since we need
        # _current_fuction to be set, and need to redefine the shortcut when
        # _current_function changes.
        self.fresh_tmp = self._current_function.fdata.fresh_tmp
        self.fresh_label = self._current_function.fdata.fresh_label
        self.add_statement = self._current_function.add_statement
        self.add_statement = self._current_function.add_statement
        self.add_instruction_PRINTLN_INT = self._current_function.add_instruction_PRINTLN_INT
        self.add_comment = self._current_function.add_comment
        self.get_label_div_by_zero = self._current_function.fdata.get_label_div_by_zero

        self._symbol_table = dict()

        self.add_comment("Variable declarations:")
        self.visit(ctx.vardecl_l())
        self.add_comment("Function body:")
        self.visit(ctx.block())
        self.add_comment("Return at end of function:")
        # This skeleton doesn't deal properly with functions, and
        # hardcodes a "return 0;" at the end of function. Generate
        # code for this "return 0;".
        self.add_statement(
            RiscV.li(Operands.A0, Operands.Immediate(0)))
        self._functions.append(self._current_function)
        del self._current_function

    def visitAssignStat(self, ctx) -> None:
        if self._debug:
            print("assign statement, rightexpression is:")
            print(Trees.toStringTree(ctx.expr(), [], self._parser))
        expr_temp = self.visit(ctx.expr())
        name = ctx.ID().getText()
        self.add_statement(RiscV.mv(self._symbol_table[name], expr_temp))

    def visitIfStat(self, ctx) -> None:
        if self._debug:
            print("if statement")
        end_if_label = self.fresh_label("end_if")
        else_block = self.fresh_label("else_block")
        expr_temp = self.visit(ctx.expr())
        if ctx.else_block is not None:
            self.add_statement(RiscV.conditional_jump(else_block,expr_temp,Condition('beq'),Operands.ZERO))
            self.visit(ctx.then_block)
            self.add_statement(RiscV.jump(end_if_label))
            self.add_statement(else_block)
            self.visit(ctx.else_block)
        else:
            self.add_statement(RiscV.conditional_jump(end_if_label,expr_temp,Condition('beq'),Operands.ZERO))
            self.visit(ctx.then_block)
       # self.visit(ctx.then_block)
        #self.add_statement(RiscV.jump(end_if_label))
        #self.add_statement(else_block)
        #if ctx.else_block is not None:
            #self.visit(ctx.else_block)
        
        self.add_statement(end_if_label)

    def visitWhileStat(self, ctx) -> None:
        if self._debug:
            print("while statement, condition is:")
            print(Trees.toStringTree(ctx.expr(), [], self._parser))
            print("and block is:")
            print(Trees.toStringTree(ctx.stat_block(), [], self._parser))
        l_cond=self.fresh_label("debut_boucle")
        l_fin=self.fresh_label("fin_boucle")
        self.add_statement(l_cond)
        expr_tmp = self.visit(ctx.expr())
        self.add_statement(RiscV.conditional_jump(l_fin,expr_tmp,Condition('beq'),Operands.ZERO))
        self.visit(ctx.stat_block())
        self.add_statement(RiscV.jump(l_cond))
        self.add_statement(l_fin)
    def visitForstat(self, ctx) -> None:
        l_cond = self.fresh_label("debut_boucle")
        l_inc = self.fresh_label("increment_boucle") # The target for continue
        l_fin = self.fresh_label("fin_boucle")

        if ctx.expr() is None:
            self.add_statement(l_cond)
            
            self._continue_stack.append(l_inc)
            self.visit(ctx.stat_block())
            self._continue_stack.pop()
            
            self.add_statement(l_inc)
            self.add_statement(RiscV.jump(l_cond))
            self.add_statement(l_fin)

        elif ctx.assignment(0) is None and ctx.assignment(1) is None and ctx.expr() is not None:
            self.add_statement(l_cond)
            expr_tmp = self.visit(ctx.expr())
            self.add_statement(RiscV.conditional_jump(l_fin, expr_tmp, Condition('beq'), Operands.ZERO))
            
            self._continue_stack.append(l_inc)
            self.visit(ctx.stat_block())
            self._continue_stack.pop()
            
            self.add_statement(l_inc)
            self.add_statement(RiscV.jump(l_cond))
            self.add_statement(l_fin)

        elif ctx.assignment(0) is not None and ctx.assignment(1) is None and ctx.expr() is not None:
            self.visit(ctx.assignment(0))
            self.add_statement(l_cond)
            expr_tmp = self.visit(ctx.expr())
            self.add_statement(RiscV.conditional_jump(l_fin, expr_tmp, Condition('beq'), Operands.ZERO))
            
            self._continue_stack.append(l_inc)
            self.visit(ctx.stat_block())
            self._continue_stack.pop()
            
            self.add_statement(l_inc)
            self.add_statement(RiscV.jump(l_cond))
            self.add_statement(l_fin)

        elif ctx.assignment(0) is not None and ctx.assignment(1) is not None and ctx.expr() is not None:
            self.visit(ctx.assignment(0))
            self.add_statement(l_cond)
            expr_tmp = self.visit(ctx.expr())
            self.add_statement(RiscV.conditional_jump(l_fin, expr_tmp, Condition('beq'), Operands.ZERO))
            
            self._continue_stack.append(l_inc)
            self.visit(ctx.stat_block())
            self._continue_stack.pop()
            
            self.add_statement(l_inc) 
            self.visit(ctx.assignment(1)) 
            
            self.add_statement(RiscV.jump(l_cond))
            self.add_statement(l_fin)

    def visitContinueStat(self, ctx) -> None:
        if not self._continue_stack:
            raise MiniCInternalError("Continue outside loop")
        self.add_statement(RiscV.jump(self._continue_stack[-1]))

            
            

                


                
            
            
        
    #def visitForstat(self,ctx) -> None:
           
    def visitPrintlnintStat(self, ctx) -> None:
        expr_loc = self.visit(ctx.expr())
        if self._debug:
            print("print_int statement, expression is:")
            print(Trees.toStringTree(ctx.expr(), [], self._parser))
        self.add_instruction_PRINTLN_INT(expr_loc)

    def visitPrintlnboolStat(self, ctx) -> None:
        expr_loc = self.visit(ctx.expr())
        self.add_instruction_PRINTLN_INT(expr_loc)

    def visitPrintlnfloatStat(self, ctx) -> None:
        raise MiniCUnsupportedError("Unsupported type float")

    def visitPrintlnstringStat(self, ctx) -> None:
        raise MiniCUnsupportedError("Unsupported type string")

    def visitStatList(self, ctx) -> None:
        for stat in ctx.stat():
            self.add_comment(Trees.toStringTree(stat, [], self._parser))
            self.visit(stat)