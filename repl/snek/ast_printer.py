import expr

class AstPrinter:
    def print_ast(self, expression: expr.Expr) -> str:
        """Traverses the AST and returns a Lisp-style string."""
        match expression:
            # If expression is a Binary node, unpack its fields into variables
            case expr.Binary(left, operator, right):
                return self.parenthesize(operator.lexeme, left, right)
            case expr.Grouping(inner_expr):
                return self.parenthesize("group", inner_expr)
            case expr.Literal(value):
                if value is None: return "nil"
                # Python stringifies True as "True", but Snek expects "true"
                if isinstance(value, bool): return str(value).lower()
                return str(value)
            case expr.Unary(operator, right):
                return self.parenthesize(operator.lexeme, right)
            case expr.Ternary(condition, then_branch, else_branch):
                return self.parenthesize("?", condition, then_branch, else_branch)
            case _:
                return "Unknown Expression"

    def parenthesize(self, name: str, *exprs: expr.Expr) -> str:
        """Helper to format nested expressions."""
        builder = [f"({name}"]
        for e in exprs:
            builder.append(f" {self.print_ast(e)}")
        builder.append(")")
        return "".join(builder)
