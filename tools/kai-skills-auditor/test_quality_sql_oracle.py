"""Differential math checks against independent SQLite aggregate/join semantics."""
import random
import sqlite3
import unittest
from quality_checks import profile_keys, profile_join


class SQLOracleTests(unittest.TestCase):
    def test_randomized_keys_match_sql(self):
        rng=random.Random(1729)
        for _ in range(60):
            rows=[{'k':rng.choice(['A','a',' B ',None])} for _ in range(rng.randrange(30))]
            con=sqlite3.connect(':memory:');self.addCleanup(con.close)
            con.execute('CREATE TABLE t(k TEXT)');con.executemany('INSERT INTO t VALUES (?)',[(r['k'],) for r in rows])
            missing=con.execute('SELECT COUNT(*) FROM t WHERE k IS NULL').fetchone()[0]
            excess=con.execute('SELECT COALESCE(SUM(n-1),0) FROM (SELECT COUNT(*) n FROM t WHERE k IS NOT NULL GROUP BY k HAVING COUNT(*)>1)').fetchone()[0]
            affected=con.execute('SELECT COALESCE(SUM(n),0) FROM (SELECT COUNT(*) n FROM t WHERE k IS NOT NULL GROUP BY k HAVING COUNT(*)>1)').fetchone()[0]
            d=profile_keys(rows,['k'])
            self.assertEqual((d['missing_key_rows'],d['duplicate_excess_rows'],d['duplicate_affected_rows']),(missing,excess,affected))

    def test_randomized_joins_match_sql(self):
        rng=random.Random(20261015)
        for _ in range(60):
            left=[{'k':rng.choice(['A','B',None])} for _ in range(rng.randrange(15))]
            right=[{'k':rng.choice(['A','B',None])} for _ in range(rng.randrange(15))]
            con=sqlite3.connect(':memory:');self.addCleanup(con.close)
            con.execute('CREATE TABLE l(k TEXT)');con.execute('CREATE TABLE r(k TEXT)')
            con.executemany('INSERT INTO l VALUES (?)',[(r['k'],) for r in left]);con.executemany('INSERT INTO r VALUES (?)',[(r['k'],) for r in right])
            inner=con.execute('SELECT COUNT(*) FROM l JOIN r ON l.k=r.k').fetchone()[0]
            outer=con.execute('SELECT COUNT(*) FROM l LEFT JOIN r ON l.k=r.k').fetchone()[0]
            d=profile_join(left,right,['k'],['k']);self.assertEqual((d['inner_join_rows'],d['left_join_rows']),(inner,outer))


if __name__=='__main__':unittest.main()
