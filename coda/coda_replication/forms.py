from django import forms
from coda_replication.models import STATUS_CHOICES

STATUS_CHOICES += [('', 'None')]


class QueueSearchForm(forms.Form):
    identifier = forms.CharField(
        widget=forms.TextInput(
            attrs={
                'id': 'prependedInput',
                'class': 'input-small',
                'placeholder': 'Ark ID',
            }
        ),
    )
    status = forms.ChoiceField(
        widget=forms.Select(
            attrs={
                'id': 'prependedInput',
                'class': 'input-medium',
            }
        ),
        choices=STATUS_CHOICES,
    )
    start_date = forms.DateField(
        widget=forms.DateInput(
            attrs={
                'id': 'startdatepicker',
                'placeholder': 'Start Date',
                'class': 'input-small',
            }
        )
    )
    end_date = forms.DateField(
        widget=forms.DateInput(
            attrs={
                'id': 'enddatepicker',
                'placeholder': 'End Date',
                'class': 'input-small',
            }
        )
    )

    def clean(self, *args, **kwargs):
        return self.cleaned_data
