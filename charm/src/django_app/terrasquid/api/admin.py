from django.contrib import admin

from .models import ACLRule, ConfigVersion, DestinationConfig, SourceACL

admin.site.register(SourceACL)
admin.site.register(DestinationConfig)
admin.site.register(ACLRule)
admin.site.register(ConfigVersion)
