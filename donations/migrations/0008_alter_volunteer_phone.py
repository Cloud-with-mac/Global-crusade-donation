from django.db import migrations, models


def remove_duplicate_phones(apps, schema_editor):
    """Delete duplicate volunteers keeping only the most recent per phone number."""
    Volunteer = apps.get_model('donations', 'Volunteer')
    seen = {}
    for v in Volunteer.objects.order_by('-submitted_at'):
        if v.phone in seen:
            v.delete()
        else:
            seen[v.phone] = v.id


class Migration(migrations.Migration):

    dependencies = [
        ('donations', '0007_volunteer_needs_transport'),
    ]

    operations = [
        migrations.RunPython(remove_duplicate_phones, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='volunteer',
            name='phone',
            field=models.CharField(max_length=30, unique=True),
        ),
    ]
