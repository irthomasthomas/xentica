"""
The collection of classes to declare and use C variables and constants.

If the logic of your ``emit()``, ``absorb()`` or ``color()`` functions
requires the intermediate variables, you must declare them via classes
from this module in the following way::

    from xentica import core

    class MyCA(core.CellularAutomaton):
        # ...

        def emit(self):
            myvar = core.IntegerVariable()

Then you can use them in mixed expressions, like::

    myvar += self.neighbors[i].buffer.state
    self.main.state = myvar & 1

You may also define constants or other ``#define`` patterns with
:class:`Constant` class.

"""
from cached_property import cached_property

from xentica.core.mixins import BscaDetectorMixin


class DeferredExpression:
    """Base class for other classes intended to be used in mixed expressions.

    In particular, it is used in base
    :class:`Variable <xentica.core.variables.Variable>` and :class:`Property
    <xentica.core.properties.Property>` classes.

    Most of the magic methods dealing with binary and unary operators,
    as well as augmented assigns are automatically overridden for this
    class. As a result, you can use its subclasses in mixed
    expressions with ordinary Python values. See the example in
    module description above.

    Allowed binary ops
        ``+``, ``-``, ``*``, ``/``, ``%``, ``>>``, ``<<``, ``&``,
        ``^``, ``|``, ``<``, ``<=``, ``>``, ``>=``, ``==``, ``!=``

    Allowed unary ops
        ``+``, ``-``, ``~``, ``abs``, ``int``, ``float``, ``round``

    Allowed augmented assigns
        ``+=``, ``-=``, ``*=``, ``/=``, ``%=``, ``<<=``, ``>>=``,
        ``&=``, ``^=``, ``|=``

    """

    def __init__(self, code=''):
        """Override arithmetic operators and augmented assigns."""
        self.code = code
        binary_ops = (
            ('+', 'add'),
            ('-', 'sub'),
            ('*', 'mul'),
            ('/', 'truediv'),
            ('%', 'mod'),
            ('>>', 'rshift'),
            ('<<', 'lshift'),
            ('&', 'and'),
            ('^', 'xor'),
            ('|', 'or'),
            ('<', 'lt'),
            ('<=', 'le'),
            ('==', 'eq'),
            ('!=', 'ne'),
            ('>', 'gt'),
            ('>=', 'ge'),
        )
        unary_ops = (
            ('-', 'neg'),
            ('+', 'pos'),
            ('abs', 'abs'),
            ('~', 'invert'),
            ('(int)', 'int'),
            ('(float)', 'float'),
            ('round', 'round'),
        )
        for c_op, base_name in binary_ops:
            def binary_direct(op):
                def op_func(self_var, value):
                    code = "(%s %s %s)" % (self_var, op, value)
                    return DeferredExpression(code)
                return op_func

            def binary_reflected(op):
                def op_func(self_var, value):
                    code = "(%s %s %s)" % (value, op, self_var)
                    return DeferredExpression(code)
                return op_func

            def augmented_assign(op):
                def op_func(self_var, value):
                    if isinstance(self_var, Variable):
                        self_var._declare_once()
                    code = "%s %s= %s;\n" % (self_var.var_name, op, value)
                    self_var._bsca.append_code(code)
                    return self
                return op_func

            func_name = "__%s__" % base_name
            setattr(self.__class__, func_name, binary_direct(c_op))
            func_name = "__r%s__" % base_name
            setattr(self.__class__, func_name, binary_reflected(c_op))
            func_name = "__i%s__" % base_name
            setattr(self.__class__, func_name, augmented_assign(c_op))

        for c_op, base_name in unary_ops:
            def unary(op):
                def op_func(self_var):
                    code = "(%s(%s))" % (op, self_var)
                    return DeferredExpression(code)
                return op_func

            func_name = "__%s__" % base_name
            setattr(self.__class__, func_name, unary(c_op))

    def __str__(self):
        """Return the code accumulated in ``self.code``."""
        return self.code


class Constant(BscaDetectorMixin):

    def __init__(self, name, value):
        self._name = name
        self._value = value
        self._pattern_name = name
        self.base_class = Constant

    def get_define_code(self):
        code = "#define %s {%s}\n" % (self._name, self._pattern_name)
        return code

    def replace_value(self, source):
        # WARNING: potentially dangerous
        val = "self._holder.%s" % self._value.split()[0]
        return source.replace("{%s}" % self._pattern_name, str(eval(val)))

    @property
    def name(self):
        return self._name


class Variable(DeferredExpression, BscaDetectorMixin):
    """
    Base class for all variables.

    """
    def __init__(self, val=None):
        super(Variable, self).__init__()
        self.base_class = Variable
        self._declared = False
        if val is not None:
            self._init_val = DeferredExpression(str(val))

    @cached_property
    def var_name(self):
        all_vars = self._holder_frame.f_locals.items()
        for k, var in all_vars:
            if isinstance(var, self.__class__):
                if hash(self) == hash(var):
                    return k
        return "var%d" % abs(hash(self))

    def _declare_once(self):
        if not self._declared:
            c = "%s %s = %s;\n" % (
                self.var_type, self.var_name, self._init_val
            )
            self._bsca.append_code(c)
            self._declared = True
            setattr(self._bsca, self.var_name, self)

    def __str__(self):
        return self.var_name

    def __get__(self, obj, objtype):
        self._declare_once()
        return self

    def __set__(self, obj, value):
        self._declare_once()
        code = "%s = %s;\n" % (self.var_name, value)
        self._bsca.append_code(code)


class IntegerVariable(Variable):
    var_type = "unsigned int"

    def __init__(self, val=0):
        super(IntegerVariable, self).__init__(val)
