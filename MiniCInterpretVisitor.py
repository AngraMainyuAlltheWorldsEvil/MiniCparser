# Visitor to *interpret* MiniC files
from typing import (
  Dict,
  List)
from MiniCVisitor import MiniCVisitor
from MiniCParser import MiniCParser
from Lib.Errors import MiniCRuntimeError, MiniCInternalError, MiniCUnsupportedError

MINIC_VALUE = int | str | bool | float | List['MINIC_VALUE']

class ContinueException(Exception):
    pass
class MiniCInterpretVisitor(MiniCVisitor):

    _memory: Dict[str, MINIC_VALUE]

    def __init__(self):
        self._memory = dict()  # store all variable ids and values.
        self.has_main = False
        self.continue_in_loop = False

    # visitors for variable declarations
 #print(self.visit(ctx.id_l()))
    def visitVarDecl(self, ctx):
        type_str = ctx.typee().getText()
        ids = self.visit(ctx.id_l())   # get list of variable names
        for var in ids:
            #print("declare", type_str, var)
            if(type_str=="int"):
                self._memory[var]=0
            if(type_str=="float"):
                self._memory[var]=0.0
            if(type_str=="string"):
                self._memory[var]=""  
            if(type_str=="bool"):
                self._memory[var]=False

    def visitIdList(self, ctx) -> List[str]:
        head = ctx.ID().getText()
        tail = self.visit(ctx.id_l())
        return [head] + tail

    def visitIdListBase(self, ctx) -> List[str]:
        return [ctx.ID().getText()]

    # visitors for atoms --> value

    def visitParExpr(self, ctx) -> MINIC_VALUE:
        return self.visit(ctx.expr())

    def visitIntAtom(self, ctx) -> int:
        return int(ctx.getText())

    def visitFloatAtom(self, ctx) -> float:
        return float(ctx.getText())

    def visitBooleanAtom(self, ctx) -> bool:
        return ctx.getText() == "true"

    def visitIdAtom(self, ctx) -> MINIC_VALUE:
        var_name = ctx.getText().strip() 
       # print("Atom " + var_name)
        if var_name not in self._memory:
            raise MiniCRuntimeError(f"Variable '{var_name}' used before declaration")
        return self._memory[var_name]

    def visitStringAtom(self, ctx) -> str:
        return ctx.getText()[1:-1]  # Remove the ""

    # visit expressions

    def visitAtomExpr(self, ctx) -> MINIC_VALUE:
        return self.visit(ctx.atom())

    def visitOrExpr(self, ctx) -> bool:
        lval = self.visit(ctx.expr(0))
        rval = self.visit(ctx.expr(1))
        return lval | rval

    def visitAndExpr(self, ctx) -> bool:
        lval = self.visit(ctx.expr(0))
        rval = self.visit(ctx.expr(1))
        return lval & rval

    def visitEqualityExpr(self, ctx) -> bool:
        assert ctx.myop is not None
        lval = self.visit(ctx.expr(0))
        rval = self.visit(ctx.expr(1))
        # be careful for float equality
        if ctx.myop.type == MiniCParser.EQ:
            return lval == rval
        else:
            return lval != rval

    def visitRelationalExpr(self, ctx) -> bool:
        assert ctx.myop is not None
        lval = self.visit(ctx.expr(0))
        rval = self.visit(ctx.expr(1))
        if ctx.myop.type == MiniCParser.LT:
            return lval < rval
        elif ctx.myop.type == MiniCParser.LTEQ:
            return lval <= rval
        elif ctx.myop.type == MiniCParser.GT:
            return lval > rval
        elif ctx.myop.type == MiniCParser.GTEQ:
            return lval >= rval
        else:
            raise MiniCInternalError(
                f"Unknown comparison operator '{ctx.myop}'"
            )

    def visitAdditiveExpr(self, ctx) -> MINIC_VALUE:
        assert ctx.myop is not None
        lval = self.visit(ctx.expr(0))
        rval = self.visit(ctx.expr(1))
        if ctx.myop.type == MiniCParser.PLUS:
            if isinstance(lval, str) or isinstance(rval, str):
                return f'{lval}{rval}'
            else:
                return lval + rval
        elif ctx.myop.type == MiniCParser.MINUS:
            return lval - rval
        else:
            raise MiniCInternalError(
                f"Unknown additive operator '{ctx.myop}'")

    def visitMultiplicativeExpr(self, ctx) -> MINIC_VALUE:
        assert ctx.myop is not None
        lval = self.visit(ctx.expr(0))
        rval = self.visit(ctx.expr(1))
        #print(self._memory)
        match ctx.myop.type:
            case MiniCParser.MULT:
                return lval * rval
            case MiniCParser.DIV:
                if(rval==0):
                   # print("division par zéro")
                    raise MiniCRuntimeError("Division by 0")
                else:
                    return  int(lval/rval)
            case MiniCParser.MOD:
                if(rval==0):
                   raise MiniCRuntimeError("Division by 0")
                else:
                    return lval - int(lval / rval) * rval

            case _: raise MiniCInternalError(
                    f"Unknown multiplicative operator '{ctx.myop}'")

    def visitNotExpr(self, ctx) -> bool:
        return not self.visit(ctx.expr())

    def visitUnaryMinusExpr(self, ctx) -> MINIC_VALUE:
        return -self.visit(ctx.expr())

    # visit statements

    def visitPrintlnintStat(self, ctx) -> None:
        val = self.visit(ctx.expr())
        assert isinstance(val, int)
        print(val)

    def visitPrintlnfloatStat(self, ctx) -> None:
        val = self.visit(ctx.expr())
        assert isinstance(val, float)
        print(f"{val:.2f}")

    def visitPrintlnboolStat(self, ctx) -> None:
        val = self.visit(ctx.expr())
        assert isinstance(val, bool)
        print('1' if val else '0')

    def visitPrintlnstringStat(self, ctx) -> None:
        val = self.visit(ctx.expr())
        assert isinstance(val, str)
        print(val)

    def visitAssignStat(self, ctx) -> None:
        #raise NotImplementedError()
        for key, value in self._memory.items():
            #print(f"{key} -> {value}")
            #print("cle " +key)
            #print(ctx.ID().getText().__class__.__name__)
            if(key==ctx.ID().getText()):
               # print("g")
               # print("op gauche"+ctx.getText().__class__.__name__)
               # print("stp")
               # print( self._memory[key].__class__.__name__)
                self._memory[ctx.ID().getText()]=self.visit(ctx.expr())
                #print("nou valeur"+self._memory[key])
            
    def visitIfStat(self, ctx) -> None:
        # raise NotImplementedError()
        #print(ctx.expr().getText())
        if(self.visit(ctx.expr())):
            #print("oui")
            self.visit(ctx.then_block)
        else:
            if ctx.else_block is not None:
                self.visit(ctx.else_block)
            
    def visitWhileStat(self, ctx) -> None:
        #raise NotImplementedError()
        while(self.visit(ctx.expr())):
            self.visit(ctx.body)
    def visitContinueStat(self, ctx) -> None:
        raise ContinueException()
                    
            
                
            
            
           
    def visitForstat(self, ctx):
        if ctx.assignment(0) is not None:
            self.visit(ctx.assignment(0))
    
        condtype = self.visit(ctx.expr()) if ctx.expr() is not None else True

        while condtype:
            try:
                self.visit(ctx.body)
            except ContinueException:
                pass  
        
            if ctx.assignment(1) is not None:
                self.visit(ctx.assignment(1))
            elif ctx.assignment(0) is not None:
                self.visit(ctx.assignment(0))
        
            condtype = self.visit(ctx.expr()) if ctx.expr() is not None else True

                

                
            
       # print(var)
        
      #  self.visit(ctx.assignment(0))
       # condtype=self.visit(ctx.expr())
       # print(ctx.expr().getText())
       # print(self.visit(ctx.expr()))
       # while(condtype):
        #    self.visit(ctx.body)
          #  print(self.visit(ctx.expr()))
           # print(self.visit(ctx.assignment(0)))
         #   self.visit(ctx.assignment(1))
          #  condtype=self.visit(ctx.expr())


    # TOPLEVEL
    def visitProgRule(self, ctx) -> None:
        self.visitChildren(ctx)
        if not self.has_main:
            # A program without a main function is compilable (hence
            # it's not a typing error per se), but not executable,
            # hence we consider it a runtime error.
            raise MiniCRuntimeError("No main function in file")

    # Visit a function: ignore if non main!
    def visitFuncDef(self, ctx) -> None:
        funname = ctx.ID().getText()
        if funname == "main":
            self.has_main = True
            self.visit(ctx.vardecl_l())
            self.visit(ctx.block())
        else:
            raise MiniCUnsupportedError("Functions are not supported in evaluation mode")
