from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('staffs', '0048_lab'),
    ]

    operations = [
        migrations.RenameField(
            model_name='lab',
            old_name='code',
            new_name='short_name',
        ),
        migrations.AlterField(
            model_name='lab',
            name='short_name',
            field=models.CharField(
                help_text='Unique short identifier for the lab (e.g. IT-LAB-01)', 
                max_length=50, 
                unique=True, 
                verbose_name='Lab Short Name'
            ),
        ),
        migrations.AddField(
            model_name='lab',
            name='from_date',
            field=models.DateField(blank=True, null=True, verbose_name='From Date'),
        ),
        migrations.AddField(
            model_name='lab',
            name='to_date',
            field=models.DateField(blank=True, null=True, verbose_name='To Date'),
        ),
    ]
