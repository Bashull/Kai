import argparse
from contextlib import redirect_stdout
import io
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import kai_phone as k


class ControlBoundaries(unittest.TestCase):
    def test_only_one_authorized_loopback_device(self):
        self.assertEqual(k.serial_from_devices('List of devices attached\n127.0.0.1:35055 device product:e3q'), '127.0.0.1:35055')
        for text in ['127.0.0.1:3 offline','127.0.0.1:3 unauthorized','192.168.1.1:3 device','127.0.0.1:70000 device','127.0.0.1:3 device\n127.0.0.1:4 device']:
            with self.assertRaises(ValueError):k.serial_from_devices(text)

    def test_remote_shell_quotes_metacharacters(self):
        adb=k.ADB.__new__(k.ADB);adb.base=['adb','-s','127.0.0.1:3']
        with patch.object(k,'run',return_value='') as run:
            adb.shell(['ls',"/sdcard/Download/a' $(id); x"])
        command=run.call_args.args[0][-1]
        import shlex
        self.assertEqual(shlex.split(command),['ls',"/sdcard/Download/a' $(id); x"])

    def test_foreground_guard(self):
        adb=k.ADB.__new__(k.ADB)
        with patch.object(adb,'foreground',return_value={'package':'com.openai.chatgpt'}):
            with self.assertRaises(ValueError):adb.guard('com.kai.controlprobe')
        self.assertEqual(k.foreground('topResumedActivity=ActivityRecord{abc u0 com.kai.controlprobe/.ProbeActivity t1}')['package'],'com.kai.controlprobe')
        self.assertIsNone(k.foreground('unknown'))

    def test_browse_rejects_traversal(self):
        for r in ['../secret','/data/user/0','a/../../b','a\0b']:
            with self.assertRaises(ValueError):k.browse_path('Download',r)
        self.assertTrue(k.browse_path('AndroidData','com.mojang.minecraftpe').endswith('/Android/data/com.mojang.minecraftpe'))

    def test_package_injection_rejected(self):
        for x in ['com.x;id','com.x/Activity','$(id)','com.x\n']:
            with self.assertRaises(ValueError):k.package(x)

    def test_private_evidence_refuses_overwrite_and_shared_storage(self):
        with tempfile.TemporaryDirectory() as d,patch.object(k,'HOME_PATH',Path(d)):
            p=Path(d)/'evidence'/'a.txt';k.private_write(p,b'one')
            with self.assertRaises(FileExistsError):k.private_write(p,b'two')
            self.assertEqual(p.read_bytes(),b'one')
            with self.assertRaises(ValueError):k.private_write(Path('/tmp/outside-evidence'),b'no')

    def test_evidence_parent_symlink_cannot_escape(self):
        with tempfile.TemporaryDirectory() as d,patch.object(k,'HOME_PATH',Path(d)):
            (Path(d)/'escape').symlink_to('/tmp',target_is_directory=True)
            with self.assertRaises(ValueError):k.private_write(Path(d)/'escape'/'capture.png',b'no')

    def test_live_find_scope_and_truncation(self):
        with tempfile.TemporaryDirectory() as d,patch.object(k,'ROOTS',{'Test':Path(d)}):
            (Path(d)/'kai-one.zip').write_text('a');(Path(d)/'kai-two.zip').write_text('b')
            (Path(d)/'.kai-secret').write_text('private');(Path(d)/'kai-link').symlink_to('/etc/passwd')
            short=k.live_find('kai','Test',1,5)
            self.assertFalse(short['complete']);self.assertEqual(short['reason'],'result_limit')
            all_=k.live_find('kai','Test',10,5)
            self.assertTrue(all_['complete']);self.assertEqual(len(all_['matches']),2)

    def test_nexus_query_is_literal(self):
        import sqlite3
        with tempfile.TemporaryDirectory() as d,patch.object(k,'HOME_PATH',Path(d)):
            p=Path(d)/'KAI_VISUAL_STUDIO/STATE/nexus_index.sqlite';p.parent.mkdir(parents=True)
            with sqlite3.connect(p) as db:
                db.execute('CREATE TABLE files(path,name,kind,size,mtime_ns,scanned_ns)')
                db.execute('INSERT INTO files VALUES(?,?,?,?,?,?)',('/a','a.zip','other',1,1,1))
            self.assertEqual(k.nexus_search("' OR 1=1 --",10)['matches'],[])
            self.assertEqual(len(k.nexus_search('.zip',10)['matches']),1)

    def test_mutation_requires_package(self):
        with patch('sys.stderr',io.StringIO()),self.assertRaises(SystemExit):k.parser().parse_args(['tap','1','1'])

    def test_subprocess_error_does_not_echo_sensitive_input(self):
        with patch.object(k.subprocess,'run',return_value=subprocess.CompletedProcess([],1,b'secret',b'credential')):
            with self.assertRaisesRegex(RuntimeError,'command_failed_exit_1') as e:k.run(['tool','private'])
            self.assertNotIn('secret',str(e.exception))

    def test_adb_preflight_cannot_consume_text_stdin(self):
        with patch.object(k.subprocess,'run',return_value=subprocess.CompletedProcess([],0,b'ok',b'')) as child:
            k.run(['adb','shell','id'])
            self.assertEqual(child.call_args.kwargs['stdin'],subprocess.DEVNULL)


if __name__=='__main__':unittest.main()
