import types
import werkzeug
import starflyer.processors as processors
from starflyer import AttributeMapper

__all__ = ['no_value', 'FormError', 'RenderContext', 'Widget', 'Form']

no_value = object()

class FormError(Exception):
    """an exception raised on validation failures"""

    def __init__(self, errors=[]):
        """initialize this exception with a list of ``Error`` instances"""
        self.errors = errors
        ed = {}
        for a,v in errors.items():
            # TODO: translate it? 
            ed[a] = v.msg
        self.error_dict = ed

class RenderContext(object):
    """a render context which annotates a widget with a settings dict"""

    def __init__(self, widget, form, **kw):
        """initialize the render context with the ``widget`` to render and
        the ``form`` the widget belongs to. We will copy the attributes
        from ``form.ctx_attrs`` to this instance and add additional keyword
        arguments to it."""
        
        self.form = form
        self.widget = widget
        self.request = form.request
        self.default = form.default
        self.attrs = AttributeMapper(form.ctx)
        self.attrs.update(kw)

    def __call__(self, widget_attrs={}, field_attrs={}, template=None):
        """render the widget. This will be called form within
        the template. You can pass additional parameters for both 
        the widget (e.g. the actual input tag) in ``widget_attrs`` 
        and the field (the surrounding structure with label etc.)
        in ``field_attrs``.

        If you wish you can also pass a new template name for the field
        to be used in ``template``. It defaults to the name define in 
        ``widget_template`` in the form class. 
        
        """
        if template is None:
            template = self.form.widget_template
        tag = self.widget.render(self, **widget_attrs)
        tmpl = self.form.template_env.get_template(template)
        error = self.form.errors.get(self.widget.name, None)
        return tmpl.render(data=self.widget, tag=tag, form = self.form, error=error, **field_attrs)

class Widget(object):
    """a field base class which emits widgets"""

    BASE_ATTRS = ['type', 'name', 'css_class', 'id']
    ATTRS = []
    INSTANCE_ATTRS = [] # add attributes here which are not to be used in the input field

    type = "text"
    css_class = ""
    messages = {
        'required' : 'This field is required'
    }

    def __init__(self, 
            name="",
            label=u"",
            description=u"",
            required=False,
            id = None,
            processors_out = [], # form data -> python (validation)
            processors_in = [], # python (db obj) -> form data
            _charset = "utf-8",
            **kw):
        self.name = name
        if id is None:
            self.id = name
        else:
            self.id = id
        if type(label) is not types.UnicodeType:
            raise ValueError("label of field %s is not Unicode" %name)
        self.label = label
        if type(description) is not types.UnicodeType:
            raise ValueError("description of field %s is not Unicode" %name)
        self.description = description
        self.required = required
        self.additional = kw
        self.processors_out = processors_out
        self.processors_in = processors_in
        for a,v in kw.items():
            if a in self.INSTANCE_ATTRS:
                setattr(self, a, v)
            

    def get_widget_value(self, form):
        """return the value to be displayed inside the widget. This will either
        come from the ``defaults`` attribute of the form or the previous request data.
        The former will usually be populated with data from an database record and
        the latter will be populated from a previous form input, e.g. on an error
        condition on a different widget."""
        n = self.name
        if form.request is not None:
            value = form.request.form.get(n, no_value)
        if value is no_value:
            value = form.default.get(n, u'')
        return value

    def get_value(self, form):
        """return the data from the form for use in Python. This will be called
        by the form processors after submitting a form. ``request`` is a werkzeug
        Request instance which should store form data in ``request.form`` and
        files in ``request.files``"""
        value = self.from_form(form)
        return self.process_out(form, value)

    def to_form(self, ctx, **kw):
        """convert a value coming from python to be used in a form by this widget.
        This can e.g. be splitting a date in date, month and year fields. A ``RenderContext``
        needs to be passed in ``ctx``"""
        n = self.name
        if ctx.request is not None:
            value = ctx.request.form.get(n, no_value)
        if value is no_value:
            value = ctx.default.get(n, u'')
        return self.process_in(value, **ctx.attrs)

    def from_form(self, form):
        """convert data received from the form to something we can pass to python.
        This can e.g. be converting three separate date, month and year fields into
        a datetime object. If errors occur you should raise an ``processors.Error`` 
        exception. Note that further processors might run afterwards. Also not
        that you receive the complete form data here as only the widget can know
        which sub fields it is using."""
        # this only is the default implementation for plain fields, adjust as you need
        # in your own widget
        value = form.request.form.get(self.name, no_value)
        if value is no_value and self.required:
            raise processors.Error('required', self.messages['required'])
        return self.process_out(value, form)

    def process_out(self, form, value, **kw):
        """run processors on data coming from this widget and being passed to python.
        The value will already be converted from form data to a single value and thus
        this runs after ``from_form()``. It should return a value or raise an
        ``processors.Error`` exception.  """
        return processors.process(value, self.processors_out, 
                form = form, 
                widget = self, **kw).data

    def process_in(self, value, **kw):
        """run processors on data coming from python and being passed to this
        widget. This will run before ``to_form()``. You might want to provide
        defaults or something similar. 

        It should return a value or raise an ``processors.Error`` exception.  
        """
        return processors.process(value, self.processors_in, **kw).data

    def render(self, render_context = None, add_class="", **kw):
        """render this widget. We also pass in the ``RenderContext`` instance
        to be used in order to be able to access the ``Form`` instance and additional
        runtime information contained within.

        Additionally you can provide an ``add_class`` parameter which can contain
        a class name to be added to the CSS classes for the input tag

        Any additional keyword arguments passed will override the original attributes
        used for rendering the tag

        Note that this method will only input e.g. a input tag and not the
        surrounding divs etc.
        """
        attrs = {}
        for a in self.BASE_ATTRS+self.ATTRS:
            attrs[a] = getattr(self, a)
        attrs.update(self.additional)
        attrs.update(kw)
        attrs['class'] = attrs['css_class']+" "+add_class
        del attrs["css_class"]

        # process the value to be displayed
        attrs['value'] = self.get_widget_value(render_context.form)

        attrs = ['%s="%s"' %(a,werkzeug.escape(v, True)) for a,v in attrs.items()]
        attrs = " ".join(attrs)
        return u"<input {0} />".format(attrs)

    def __call__(self, form):
        """return a render context"""
        return RenderContext(self, form)


class Form(object):
    """a form"""

    error_css_class = "error"
    widget_template = "widget.html"
    widgets = [] # list of Widget instances
    processors_in = []
    processors_out = []

    def __init__(self, 
                 template_env=None, 
                 default = {}, 
                 request = None, 
                 errors= {}, 
                 vocabs = {},
                 ctx = {}):
        """initialize the form's widget. We pass in a ``tmpl_env`` which is a 
        ``jinja2.Environment`` and should contain a template called ``field.html``
        to be used for rendering a single field. Optionally you can pass in 
        ``vocabs`` which should contain the vocabularies to be used for select
        fields etc. ``default`` is a dictionary with which you can pass in data
        into the form as initial values. ``request`` is a werkzeug Request object
        from which we read files and form data"""
        self.template_env = template_env
        self.vocabs = vocabs
        self.default = default # this might come from an object
        self.request = request # this might come from a form and overrides the defaults
        self.errors = errors
        self.data = {}
        self.ctx = ctx
        for widget in self.widgets:
            self.data[widget.name] = widget
        
        # run incoming processors to create the defaults
        self.default =  processors.process(self.default, self.processors_in, **ctx).data

    def __getitem__(self, widget_name):
        """return a render context"""
        widget = self.data[widget_name]
        return widget(self)

    __getattr__ = __getitem__

    @property
    def has_errors(self):
        """return if this is a form with errors which basically means that
        it is a form which was submitted before and we call it again with errors"""
        return self.errors != {}

    def process(self, obj=None, **kw):
        """run the out processors on all widgets.
        
        :param obj: optional database object etc. which can be passed in. It will be
                used in the form related processors
        :param **kw: additional keyword arguments will be passed to the ``ProcessorContext``
            instance.
        :return: a data dictionary with ``formdata`` and ``obj``.
        """
        result = {}
        errors = {}
        for n, widget in self.data.items():
            try: 
                result[n] = widget.get_value(self)
            except processors.Error, e:
                errors[n] = e
        if len(errors.keys()) > 0:
            raise FormError(errors)

        value = {
            'obj' : obj,
            'formdata' : result
        }
        return processors.process(value, self.processors_out, **kw).data

