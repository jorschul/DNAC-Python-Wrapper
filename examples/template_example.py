#!/usr/bin/env python

from __init__.dnac import Dnac
from __init__.dnac import Template, TARGET_BY_ID

MODULE = 'template_example.py'

print('%s: preparing to deploy a template...' % MODULE)

dnac = Dnac()

template = Template(dnac, 'Set VLAN')

print('%s: setting the target device...' % MODULE)

dnac.api['Set VLAN'].targetId = '84e4b133-2668-4705-8163-5694c84e78fb'
dnac.api['Set VLAN'].targetType = TARGET_BY_ID

print('%s: setting the template\'s parameters...' % MODULE)

dnac.api['Set VLAN'].versionedTemplateParams['interface'] = 'g1/0/8'
dnac.api['Set VLAN'].versionedTemplateParams['description'] = 'Provisioned by %s' % MODULE
dnac.api['Set VLAN'].versionedTemplateParams['vlan'] = 10

print('%s: deploying the template...' % MODULE)

dnac.api['Set VLAN'].deploy_sync()

print('%s: deploy results: %s' % (MODULE, dnac.api['Set VLAN'].deployment.results))

print()