from django import forms
 
 
class EditorForm(forms.Form):
    code = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'w-100 h-100'
        }),
        required=False,
    )
    file_name = forms.CharField(
        required=False,
    )