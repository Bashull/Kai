"""Directed public-format examples and rejected mixed-format authoring inputs."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

spec=importlib.util.spec_from_file_location('manifest008',Path(__file__).with_name('inspect_context_package.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


class ContextManifestExamples(unittest.TestCase):
    def test_new_portable_fixed_discovery_format(self):
        p={'$schema':m.SCHEMA,'name':'context-example-product','version':'0.2.0','author':{'name':'Example maintainer'}}
        r=m.resolve_manifests(p);self.assertEqual(r['format'],'AGENT_PLUGINS_1.0.0');self.assertEqual(r['openai_settings_source'],'none')

    def test_approved_codex_stays_compatible_without_migration(self):
        c={'name':'context-existing','version':'0.1.0','skills':'./skills/'}
        self.assertEqual(m.resolve_manifests(compatibility=c)['format'],'CODEX_COMPATIBILITY')

    def test_empty_inline_object_does_not_inherit_overlay(self):
        p={'$schema':m.SCHEMA,'name':'root-owner','extensions':{'com.openai':{}}}
        c={'name':'overlay-owner','interface':{'displayName':'Overlay branding'}}
        self.assertEqual(m.resolve_manifests(p,c)['effective_openai_settings'],{})
        self.assertEqual(m.resolve_manifests(p,c)['name'],'root-owner')

    def test_partial_inline_object_does_not_merge_other_overlay_fields(self):
        p={'$schema':m.SCHEMA,'name':'root-owner','extensions':{'com.openai':{'onboardingSkill':'./skills/start/SKILL.md'}}}
        c={'interface':{'displayName':'Overlay'},'apps':'./.app.json'}
        r=m.resolve_manifests(p,c);self.assertEqual(r['effective_openai_settings'],p['extensions']['com.openai']);self.assertEqual(r['openai_settings_source'],'portable-inline')

    def test_absent_inline_uses_overlay_without_overriding_root_identity(self):
        p={'$schema':m.SCHEMA,'name':'root-owner','version':'0.2.0'}
        c={'name':'overlay-owner','version':'0.1.0','interface':{'displayName':'Overlay'}}
        r=m.resolve_manifests(p,c);self.assertEqual(r['name'],'root-owner');self.assertEqual(r['version'],'0.2.0');self.assertEqual(r['effective_openai_settings'],c)

    def test_renamed_codex_fields_are_not_portable_schema_fields(self):
        for field,value in [('skills','./skills/'),('interface',{}),('mcpServers',{})]:
            with self.subTest(field=field):
                with self.assertRaisesRegex(ValueError,'Nonportable'):m.portable_shape({'$schema':m.SCHEMA,'name':'example',field:value})

    def test_unsupported_version_or_wrong_typed_fields_are_not_certified(self):
        for p in [{'$schema':m.SCHEMA.replace('1.0.0','9.0.0'),'name':'example'}, {'$schema':m.SCHEMA,'name':'example','author':{'name':4}}, {'$schema':m.SCHEMA,'name':'example','extensions':{'com.openai':None}}]:
            with self.subTest(p=p):
                with self.assertRaises(ValueError):m.portable_shape(p)

    def test_zip_traversal_is_refused_without_extracting(self):
        with tempfile.TemporaryDirectory(prefix='kai-context008-') as d:
            p=Path(d)/'bad.zip'
            with zipfile.ZipFile(p,'w') as z:z.writestr('../external.txt','leave outside alone')
            with self.assertRaises(ValueError):m.inspect(p)
            self.assertEqual([x.name for x in Path(d).iterdir()],['bad.zip'])

    def test_context_zip_with_directory_entries_is_read_without_extraction(self):
        with tempfile.TemporaryDirectory(prefix='kai-context008-') as d:
            p=Path(d)/'good.zip'
            with zipfile.ZipFile(p,'w') as z:
                z.writestr('skills/','');z.writestr('skills/context-example/','')
                z.writestr('plugin.json',json.dumps({'$schema':m.SCHEMA,'name':'context-example'}))
                z.writestr('skills/context-example/SKILL.md','---\nname: context-example\ndescription: Use for fictional product analysis.\n---\n\nApply reviewed fictional product definitions.\n')
            r=m.inspect(p);self.assertEqual(r['status'],'DIRECTED_CHECKS_PASS');self.assertEqual(len(r['skills']),1)
            self.assertEqual([x.name for x in Path(d).iterdir()],['good.zip'])


if __name__=='__main__':unittest.main(verbosity=2)
