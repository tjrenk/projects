from django import forms
from django.contrib.auth.forms import PasswordChangeForm


class CustomPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add custom CSS classes or placeholders to the form widgets
        for field_name, field in self.fields.items():
            field.widget.attrs.update({
                'class': 'form-control block w-full px-3 py-2 border rounded-md shadow-sm',
                'placeholder': f'Enter {field.label.lower()}'
            })