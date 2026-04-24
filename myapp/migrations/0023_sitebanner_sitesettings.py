from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0022_cartitem_unit_price'),
    ]

    operations = [
        migrations.CreateModel(
            name='SiteBanner',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=100)),
                ('subtitle', models.CharField(blank=True, max_length=200)),
                ('image', models.ImageField(upload_to='banners/')),
                ('link_url', models.CharField(default='/', max_length=200)),
                ('is_active', models.BooleanField(default=True)),
                ('order', models.PositiveIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'Site Banner',
                'verbose_name_plural': 'Site Banners',
                'ordering': ['order'],
            },
        ),
        migrations.CreateModel(
            name='SiteSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sale_text', models.CharField(default='Mega Summer Sale - Up to 50% Off!', max_length=200)),
                ('is_sale_active', models.BooleanField(default=True)),
            ],
            options={
                'verbose_name': 'Site Settings',
                'verbose_name_plural': 'Site Settings',
            },
        ),
    ]
