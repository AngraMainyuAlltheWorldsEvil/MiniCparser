# Visitor to *typecheck* MiniC files
from typing import List, NoReturn
from MiniCVisitor import MiniCVisitor
from MiniCParser import MiniCParser
from Lib.Errors import MiniCInternalError, MiniCTypeError

from enum import Enum


class BaseType(Enum):
    Float, Integer, Boolean, String = range(4)


# Basic Type Checking for MiniC programs.
class MiniCTypingVisitor(MiniCVisitor):

    def __init__(self):
        self._memorytypes = dict()  # id -> types
        self._current_function = "main"

    def _raise(self, ctx, for_what, *types):
        raise MiniCTypeError(
            f"In function {self._current_function}:"
            f" Line {ctx.start.line} col {ctx.start.column}:"
            f" invalid type for {for_what}:"
            f" {' and '.join(t.name.lower() for t in types)}")

    def _assertSameType(self, ctx, for_what, *types):
        if not all(types[0] == t for t in types):
            raise MiniCTypeError(
                f"In function {self._current_function}:"
                f" Line {ctx.start.line}"
                f" col {ctx.start.column}:"
                f" type mismatch for {for_what}:"
                f" {' and '.join(t.name.lower() for t in types)}")

    def _raiseNonType(self, ctx, message) -> NoReturn:
        raise MiniCTypeError(
            f"In function {self._current_function}:"
            f" Line {ctx.start.line}"
            f" col {ctx.start.column}: {message}")

    # type declaration

    def visitVarDecl(self, ctx) -> None:
        vars_l = self.visit(ctx.id_l())
        tt = self.visit(ctx.typee())
        for name in vars_l:
            if name in self._memorytypes:
                self._raiseNonType(ctx,
                                   f"Variable {name} already declared")
            self._memorytypes[name] = tt

    def visitBasicType(self, ctx):
        assert ctx.mytype is not None
        if ctx.mytype.type == MiniCParser.INTTYPE:
            return BaseType.Integer
        elif ctx.mytype.type == MiniCParser.FLOATTYPE:
            return BaseType.Float
        elif ctx.mytype.type == MiniCParser.BOOLTYPE:
            return BaseType.Boolean
        elif ctx.mytype.type == MiniCParser.STRINGTYPE:
            return BaseType.String
        else:
            raise MiniCInternalError("Type not implemented")

    def visitIdList(self, ctx) -> List[str]:
        t = self.visit(ctx.id_l())
        t.append(ctx.ID().getText())
        return t

    def visitIdListBase(self, ctx) -> List[str]:
        return [ctx.ID().getText()]

    # typing visitors for expressions, statements !

    # visitors for atoms --> type
    def visitParExpr(self, ctx):
        return self.visit(ctx.expr())

    def visitIntAtom(self, ctx):
        return BaseType.Integer

    def visitFloatAtom(self, ctx):
        return BaseType.Float

    def visitBooleanAtom(self, ctx):
        return BaseType.Boolean

    def visitIdAtom(self, ctx):
        try:
            return self._memorytypes[ctx.getText()]
        except KeyError:
            self._raiseNonType(ctx,
                               f"Undefined variable {ctx.getText()}")

    def visitStringAtom(self, ctx):
        return BaseType.String

    # now visit expr

    def visitAtomExpr(self, ctx):
        return self.visit(ctx.atom())

    def visitOrExpr(self, ctx):
        ltype = self.visit(ctx.expr(0))
        rtype = self.visit(ctx.expr(1))
        if BaseType.Boolean == ltype and BaseType.Boolean == rtype:
            return BaseType.Boolean
        else:
            self._raise(ctx, 'boolean operands', ltype, rtype)

    def visitAndExpr(self, ctx):
        return self.visitOrExpr(ctx)  # Same typing rules

    def visitEqualityExpr(self, ctx):
        ltype = self.visit(ctx.expr(0))
        rtype = self.visit(ctx.expr(1))

        self._assertSameType(ctx, 'equality operands', ltype, rtype)

        return BaseType.Boolean

    def visitRelationalExpr(self, ctx):
        ltype = self.visit(ctx.expr(0))
        rtype = self.visit(ctx.expr(1))

        if ltype != rtype:
            self._raise(ctx, 'relational operands', ltype, rtype)

        if ltype not in (BaseType.Integer, BaseType.Float):
            self._raise(ctx, 'relational operands', ltype, rtype)

        return BaseType.Boolean

    def visitAdditiveExpr(self, ctx):
        assert ctx.myop is not None
        ltype = self.visit(ctx.expr(0))
        rtype = self.visit(ctx.expr(1))

        if ltype != rtype:
            self._raise(ctx, 'additive operands', ltype, rtype)
        if ltype not in (BaseType.Integer, BaseType.Float, BaseType.String):
            self._raise(ctx, 'additive operands', ltype, rtype)
        if ctx.myop.type != MiniCParser.PLUS and ltype == BaseType.String:
            self._raise(ctx, 'additive operands', ltype, rtype)

        return ltype

    def visitMultiplicativeExpr(self, ctx):
        assert ctx.myop is not None
        ltype = self.visit(ctx.expr(0))
        rtype = self.visit(ctx.expr(1))

        if ltype != rtype:
            self._raise(ctx, 'multiplicative operands', ltype, rtype)

        if ltype not in (BaseType.Integer, BaseType.Float):
            self._raise(ctx, 'multiplicative operands', ltype, rtype)

        if ctx.myop.type == MiniCParser.MOD and ltype != BaseType.Integer:
            self._raise(ctx, 'non-integer modulo', ltype, rtype)

        return ltype

    def visitNotExpr(self, ctx):
        etype = self.visit(ctx.expr())
        if etype != BaseType.Boolean:
            self._raise(ctx, 'not expression', etype)
        else:
            return BaseType.Boolean

    def visitUnaryMinusExpr(self, ctx):
        etype = self.visit(ctx.expr())
        if etype not in (BaseType.Integer, BaseType.Float):
            self._raise(ctx, 'unary minus operand', etype)

        return etype

    # visit statements

    def visitPrintlnintStat(self, ctx):
        etype = self.visit(ctx.expr())
        if etype != BaseType.Integer:
            self._raise(ctx, 'println_int statement', etype)

    def visitPrintlnfloatStat(self, ctx):
        etype = self.visit(ctx.expr())
        if etype != BaseType.Float:
            self._raise(ctx, 'println_float statement', etype)

    def visitPrintlnboolStat(self, ctx):
        etype = self.visit(ctx.expr())
        if etype != BaseType.Boolean:
            self._raise(ctx, 'println_bool statement', etype)

    def visitPrintlnstringStat(self, ctx):
        etype = self.visit(ctx.expr())
        if etype != BaseType.String:
            self._raise(ctx, 'println_string statement', etype)

    def visitAssignStat(self, ctx):
        exprtype = self.visit(ctx.expr())
        name = ctx.ID().getText()
        if name not in self._memorytypes:
            self._raiseNonType(
                ctx, "Undefined variable "+name)
        self._assertSameType(
            ctx, name, self._memorytypes[name], exprtype)

    def visitWhileStat(self, ctx):
        condtype = self.visit(ctx.expr())
        if condtype != BaseType.Boolean:
            self._raise(ctx, 'while condition', condtype)
        self.visit(ctx.body)
    def visitForstat(self,ctx):
        if(ctx.expr()!=None):
            condtype = self.visit(ctx.expr())
        
            if( ctx.assignment(0)!=None):
           #     print("hi")
                ass0=self.visit(ctx.assignment(0))
            if(ctx.assignment(1)!=None):
                ass1 = self.visit(ctx.assignment(1))

             #   print("hi2")
            
        #print(ass)
            if condtype !=BaseType.Boolean:
                self._raise(ctx,'for condition',condtype)
        #if ass !=BaseType.Integer:
           # self._raise(ctx,'for condition',ass)

            
        self.visit(ctx.body)
        
    
    def visitIfStat(self, ctx):
        condtype = self.visit(ctx.expr())
        if condtype != BaseType.Boolean:
            self._raise(ctx, 'if condition', condtype)
        self.visit(ctx.then_block)
        if ctx.else_block is not None:
            self.visit(ctx.else_block)
