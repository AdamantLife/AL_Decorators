## Builtin Modules
import functools, inspect

def signature_decorator_factory(*callbacks, apply_defaults = False):
    """ Creates a decorator which calls the given functions before applying the decorated function.
    
        The functions passed to callbacks should accept a single argument, which is a BoundArguments
        instance for the current decorated function call.
        If apply_defaults is True (defualt False), BoundArguments.apply_defaults will be called 
        before the first callback is called.

        Example Usage:

        def update_foo(bargs):
            \""" If the foo argument is missing, sets foo to 123456789. \"""
            bargs.apply_defaults()
            if bargs.arguments['foo'] == None:
                bargs.arguments['foo'] = 123456789

        foo_decorator = signature_decorator_factory(update_foo)

        @foo_decorator
        def my_foo(foo): return foo

        @foo_decorator
        def your_foo(*, foo = None): return foo

        my_foo(None)
        > 123456789

        my_foo(foo = None):
        > 123456789

        your_foo():
        > 123456789


        Note that this example can be more easily implemented using the dynamic_defaults
        function below which extends SignatureDecorator.factory.
    """
    def decorator(func):
        sig = inspect.signature(func)
        @functools.wraps(func)
        def inner(*args,**kw):
            ba = sig.bind(*args,**kw)
            if apply_defaults: ba.apply_defaults()
            for callback in callbacks:
                callback(ba)
            return func(*ba.args,**ba.kwargs)
        return inner
    return decorator

class SignatureDecorator():
    """ A class-based implementation of signature_decorator_factory
        which also allows for greater interspection of the function being decorated
        
        
        Usage is similar to signature_decorator_factory. SignatureDecorator has an
        additional argument called apply_self which causes the decorator to pass this
        SignatureDecorator instance to callables instead of the BoundArguments for the
        current call. Also, a single SignatureDecorator instance cannot be reused for
        multiple function unlike signature_decorator_factory, but the class has a
        classmethod which fills that role (SignatureDecorator.factory)

        def update_foo(SigDec):
            \""" If the function has a foo parameter and it has not been assigned, set it to 123456789. \"""
            ba = SigDec.boundarguments
            if "foo" in SigDec.parameters:
                if "foo" not in ba.arguments:
                    ba['foo'] = 123456789
            ba.apply_defaults()

        foo_decorator = SignatureDecorator(update_foo)

        @foo_decorator
        def my_foo(a, foo = None): return foo

        my_foo("bar")
        > 123456789

        // Cannot reuse foo_decorator on another function
        @foo_decorator
        def another_foo(foo): return foo
        > AttributeError("SignatureDecorator can only be initialized for a single function (see SignatureDecorator.factory)")


        foo_too = SignatureDecorator(update_foo, apply_defaults)

        @foo_too
        def your_foo(bizzbuzz = 0): return bizzbuzz

        // "foo" i not in SigDec.parameters, so update_foo
        // can determine not to check for "foo" in ba.arguments
        // and subsequently add it to the bound arguments
        your_foo()
        > 0
        """
    def __init__(self, *callbacks, apply_defaults = False, apply_self = True):
        """ Creates a new SignatureDecorator which can be applid to a function.

            The functions passed to callbacks should accept a single argument, as described by apply_self.
            If apply_defaults is True (default False), BoundArguments.apply_defaults will be called 
            before the first callback is called.
            If apply_self is True (default), callbacks are passed this SignatureDecorator instance.
            Otherwise, the BoundArguments for the current call are passed to them.
        """
        self._callbacks = callbacks
        self._apply_defaults = apply_defaults
        self._apply_self = apply_self
        self._func = None
        self._signature = None
        self._boundarguments = None
        self._isset = False

    ## These attributes shouldn't really be changed after instantiation
    @property
    def callbacks(self):
        return tuple(self._callbacks)
    @property
    def apply_defaults(self):
        return self._apply_defaults
    @property
    def apply_self(self):
        return self._apply_self
    @property
    def func(self):
        return self._func
    @property
    def signature(self):
        return self._signature

    def __call__(self,func):
        """ Decorates a function as described in the class description. """
        if self._isset:
            raise AttributeError("SignatureDecorator can only be initialized for a single function (see SignatureDecorator.factory)")
        self._func = func
        self._signature = inspect.signature(func)
        @functools.wraps(func)
        def inner(*args,**kw):
            ba = self.boundarguments = self.signature.bind(*args,**kw)
            if self.apply_defaults: ba.apply_defaults()
            for callback in self.callbacks:
                if self.apply_self: callback(self)
                else: callback(ba)
            return func(*ba.args,**ba.kwargs)

        return inner

    @classmethod
    def factory(cls,*callbacks, apply_defaults = False, apply_self = False, ondecoration = None):
        """ Classmethod for SignatureDecorator which spawns a new SignatureDecorator
            with the given settings each time it decorates a function.

            Arguments are identical to SignatureDecorator initialization with one addition:
            ondecoration if provided should be a callable which can recieve the created
            SignatureDecorator created by this function. ondecoration is called after the
            function has been decorated, but before the decorated function is returned.

            Example Usage:
                def update_foo(bargs):
                \""" If the foo argument is missing, sets foo to 123456789. \"""
                bargs.apply_defaults()
                if bargs.arguments['foo'] == None:
                    bargs.arguments['foo'] = 123456789

                foo_decorator = SignatureDecorator.factory(update_foo)

                // Unlike signature_decorator_factory or SignatureDecorator instances
                // this line first creates a new SignatureDecorator instance and then
                // returns the result of that new Instance.__call__(my_foo)
                @foo_decorator
                def my_foo(foo): return foo

                @foo_decorator
                def your_foo(*, foo = None): return foo

                my_foo(None)
                > 123456789

                my_foo(foo = None):
                > 123456789

                your_foo():
                > 123456789
        """
        def inner(func):
            inst = cls(*callbacks,apply_defaults = apply_defaults, apply_self = apply_self)
            deco = functools.wraps(func)(inst(func))
            if ondecoration:
                ondecoration(inst)
            return deco
        return inner

def dynamic_defaults(**kw):
    """ A factory to help implement the most common usage of signature_decorator_factory:
        implementing default values that are reliant on other pieces of code or otherwise
        are not intended for the signature line.
        
        Accepts any keyword arguments that can be accepted by the underlying function.
        The values can be callables which will be invoked if the default value is required,
        if so, they will not be passed any arguments. If the value is not callable, it will
        be used as-is.

        Returns a decorator to apply to the function with the dynamic default value.

        Usage Example:

        ## An arbitrary bit of data upon which sayHello's
        ## default value relies, but whose state cannot
        ## be garaunteed
        user = {}

        ## A function that would generate the default value
        def default_username():
            if user.get("name"): return user['name']
            else: return "World"
            
        ## Use the result of dynamic_defaults() as a decorator
        ## 
        @dynamic_defaults(name = default_username)
        def sayHello(name = None):
            print(f"Hello {name}")

        sayHello()
        > "Hello World"

        user['name'] = "Hello'
        sayHello()
        > "Hello Hello"

    """
    def ondecoration(sigdecor):
        params = sigdecor.signature.parameters
        for k in kw:
            if k not in params:
                raise TypeError(f"dynamic_defaults got an unexpected keyword argument for the function {sigdecor.func.__name__}: {k}")

    def update(sigdecor):
        ba = sigdecor.boundarguments
        for (k,v) in kw.items():
            if k not in ba.arguments:
                try: ba.arguments[k] = v()
                except: ba.arguments[k] = v    
        ba.apply_defaults()
    return SignatureDecorator.factory(update, apply_defaults = False, apply_self = True, ondecoration = ondecoration)
            
def defaultproperty(func):
    """ Convenience function which returns a property decorator which
        manages a variable alongside the decorated function: when the
        variable is set, the set value is returned by the getter;
        when it is not set, the function result is returned instead.
        The setter and deleter are generated automatically.

        When setting the property, the variable name is stored on the
        object as "_"+property_name and the value is set as-is; in other
        words, setting the property to a different function will not
        change the default function and will return the function object
        without calling it.
        
        To clear the variable, use "del".

        Example usage:

            MyClass():
                @defaultproperty
                def x():
                    return 22/7

            foo = MyClass()
            foo.x
            >>> 3.142857142857143
            
            foo.x = (1+5**.5)/2
            foo.x
            >>> 1.618033988749895

            del x
            foo.x
            >>> 3.142857142857143
        """
    name = func.__name__
    varname = "_"+name
    

    def setter(self,value):
        setattr(self,varname,value)

    def deleter(self):
        delattr(self,varname)

    @functools.wraps(func)
    def inner(self,*args,**kw):
        try: return getattr(self,varname)
        except AttributeError: return func(self,*args,**kw)

    return property(fget = inner, fset = setter, fdel = deleter)