from rpython.rlib import jit

from hippy.objects.base import W_Root as WPHP_Root
from hippy.objects.reference import W_Reference as Wpy_Reference

from pypy.interpreter.baseobjspace import W_Root as WPy_Root
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.gateway import interp2app


class PHP_Scope(WPy_Root):
    _immutable_fields_ = ["ph_interp", "ph_frame"]

    def __init__(self, ph_interp, ph_frame):
        self.ph_interp = ph_interp
        self.ph_frame = ph_frame


    def py_lookup(self, n):
        """Lookup 'n' in this scope and return it as a PyPy object or None
        if not found."""
    
        ph_interp = self.ph_interp
        ph_frame = self.ph_frame

        bc = jit.promote(ph_frame.bytecode)
        no = bc.lookup_var_pos(n)
        if no >= 0:
            ph_v = ph_frame.lookup_deref(no, one_level=True)
            if ph_v is not None:
                return ph_v.to_py(ph_interp)
            return None

        ph_v = ph_interp.lookup_constant(n)
        if ph_v is not None:
            return ph_v.to_py(ph_interp)

        ph_v = ph_interp.lookup_function(n)
        if ph_v is not None:
            return ph_v.to_py(ph_interp)

        ph_v = ph_interp.lookup_class_or_intf(n)
        if ph_v is not None:
            return ph_v.to_py(ph_interp)

        py_scope = ph_frame.bytecode.py_scope
        if py_scope is not None:
            return py_scope.py_lookup(n)


class W_PHPGlobalScope(WPy_Root):
    """Proxy the global PHP namespace."""

    _immutable_fields_ = ["interp"]

    def __init__(self, interp):
        self.interp = interp

    def get_php_interp(self):
        return self.interp

    def descr_get(self, w_name):
        ph_interp = self.interp
        py_space = ph_interp.pyspace

        n = py_space.str_w(w_name)
        ph_v = ph_interp.lookup_constant(n)
        if ph_v is not None:
            return ph_v.to_py(ph_interp)

        ph_v = ph_interp.lookup_function(n)
        if ph_v is not None:
            return ph_v.to_py(ph_interp)

        ph_v = ph_interp.lookup_class_or_intf(n)
        if ph_v is not None:
            return ph_v.to_py(ph_interp)

        print "can't find", n
        assert False

W_PHPGlobalScope.typedef = TypeDef("PHPGlobalScope",
    __getattr__ = interp2app(W_PHPGlobalScope.descr_get),
    #__setattr__ = interp2app(W_PHPProxyGeneric.descr_set),
)


class Py_Scope(WPHP_Root):
    _immutable_fields_ = ["py_interp", "py_frame"]

    def __init__(self, py_interp, py_frame):
        self.py_interp = py_interp
        self.py_frame = py_frame


    def ph_lookup(self, n):
        """Lookup 'n' in this scope and return it as a Hippy object or None
        if not found."""

        py_v = self.py_lookup(n)
        if py_v is not None:
            return py_v.to_php(self.py_interp.get_php_interp())
        return None


    def py_lookup(self, n):
        """Lookup 'n' in this scope and return it as a PyPy object or
        not found."""

        py_frame = self.py_frame
        py_interp = self.py_interp

        # Look in regular Python scope
        py_frame.fast2locals()
        py_v = py_interp.finditem_str(py_frame.w_locals, n)
        if py_v is not None:
            return py_v

        # Look in Python globals
        py_v = py_interp.finditem_str(py_frame.w_globals, n)

        if py_v is not None:
            return py_v

        php_scope = py_frame.php_scope
        if php_scope is not None:
            return php_scope.py_lookup(n)
        return None
