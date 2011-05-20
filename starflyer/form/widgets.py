from core import Widget, no_value
from starflyer.processors import Error
import werkzeug

__all__ = ['Text', 'Password', 'Email', 'URL', 'File', 'DatePicker', 'Checkbox', 
           'Select', 'Textarea', 'Input']

class Input(Widget):
    """an input widget"""

    def from_form(self, request, **kw):
        """check if the value is an empty string or missing and raise an
        exception in case it is required."""
        v = request.form.get(self.name, no_value)
        if (v is no_value or v.strip()=="") and self.required:
            raise Error('required', self.messages['required'])
        return v

class Text(Input):
    """a text input field"""

    type="text"
    css_class="widget widget-text"
    ATTRS = ['size','maxlength']
    size=10
    maxlength =100

class Password(Text):
    """an password input field"""

    css_class="widget widget-password"
    type="password"

class Email(Text):
    """a text widget"""

    css_class="widget widget-email"
    type="email"

class URL(Text):
    """an URL input field"""

    css_class="widget widget-url"
    type="url"

class File(Text):
    """an file input field"""

    css_class="widget widget-file"
    type="file"

    def from_form(self, request, **kw):
        """check if the value is an empty string or missing and raise an
        exception in case it is required."""
        v = request.files.get(self.name, no_value)
        print dir(v)
        if v is no_value and self.required:
            raise Error('required', self.messages['required'])
        return v

class DatePicker(Text):
    """a datepicker widget which can be enhanced by jquery etc.
    The JS code is not included and thus you have to initialize the widget
    yourself in your template."""

    css_class="widget widget-datepicker"

class Checkbox(Widget):
    """a checkbox input field"""

    css_class="widget widget-checkbox"
    type="checkbox"

    # TODO: make it do something, e.g. set checked

class Select(Widget):
    """a select widget. In order to work this widget also needs
    a source for the options to display. As this list might be dynamically
    we cannot pass it to the ``Widget`` constructor but instead we will
    assume it to be retrieved from ``self.form.options[widget.name]()``"""

    css_class="widget widget-select"
    ATTRS = ['multiple']
    multiple = None

    def __init__(self,*args, **kwargs):
        """initialize the select widget wich an optional set of fixed options"""
        self.options = kwargs.get('options', None)
        if kwargs.has_key("options"):
            del kwargs['options']
        super(Select, self).__init__(*args, **kwargs)

    def render(self, context):
        """render this widget."""

        # create the select field
        attrs = {}
        for a in self.BASE_ATTRS+self.ATTRS:
            attrs[a] = getattr(self, a)
        attrs.update(self.additional)
        attrs['class'] = attrs['css_class']
        del attrs["css_class"]

        if attrs['multiple'] is None:
            del attrs['multiple']
        attrs = ['%s="%s"' %(a,werkzeug.escape(v, True)) for a,v in attrs.items()]
        attrs = " ".join(attrs)

        # add the options, this should return a list of tuples of (key, value)
        if self.options is None:
            options = context.form.vocabs[self.name]
            if callable(options):
                options = options()
        else:
            options = self.options
        options = ['<option value="%s">%s</option>' %(werkzeug.escape(a, True),werkzeug.escape(v, True)) for a,v in options]
        options = "\n".join(options)

        return u"<select {0}>{1}</select>".format(attrs, options)

class Textarea(Widget):
    """a select widget. In order to work this widget also needs
    a source for the options to display. As this list might be dynamically
    we cannot pass it to the ``Widget`` constructor but instead we will
    assume it to be retrieved from ``self.form.options[widget.name]()``"""

    css_class="widget widget-textarea"
    ATTRS = ['cols', 'rows']
    cols = 40
    rows = 10

    def from_form(self, request, **kw):
        """check if the value is an empty string or missing and raise an
        exception in case it is required."""
        v = request.form.get(self.name, no_value)
        if (v is no_value or v.strip()=="") and self.required:
            raise Error('required', self.messages['required'])
        return v

    def render(self, render_context):
        """render this widget."""

        # create the select field
        attrs = {}
        for a in self.BASE_ATTRS+self.ATTRS:
            attrs[a] = getattr(self, a)
        attrs.update(self.additional)
        attrs['class'] = attrs['css_class']
        del attrs["css_class"]

        value = self.get_widget_value(render_context.form)

        attrs = ['%s="%s"' %(a,werkzeug.escape(v, True)) for a,v in attrs.items()]
        attrs = " ".join(attrs)

        return u"<textarea {0}>{1}</textarea>".format(attrs, value)
