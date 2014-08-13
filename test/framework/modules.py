##
# Copyright 2012-2014 Ghent University
#
# This file is part of EasyBuild,
# originally created by the HPC team of Ghent University (http://ugent.be/hpc/en),
# with support of Ghent University (http://ugent.be/hpc),
# the Flemish Supercomputer Centre (VSC) (https://vscentrum.be/nl/en),
# the Hercules foundation (http://www.herculesstichting.be/in_English)
# and the Department of Economy, Science and Innovation (EWI) (http://www.ewi-vlaanderen.be/en).
#
# http://github.com/hpcugent/easybuild
#
# EasyBuild is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation v2.
#
# EasyBuild is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with EasyBuild.  If not, see <http://www.gnu.org/licenses/>.
##
"""
Unit tests for modules.py.

@author: Toon Willems (Ghent University)
@author: Kenneth Hoste (Ghent University)
@author: Stijn De Weirdt (Ghent University)
"""

import os
import re
import tempfile
import shutil
from test.framework.utilities import EnhancedTestCase, init_config
from unittest import TestLoader, main

from easybuild.tools.build_log import EasyBuildError
from easybuild.tools.modules import get_software_root, get_software_version, get_software_libdir, modules_tool


# number of modules included for testing purposes
TEST_MODULES_COUNT = 38


class ModulesTest(EnhancedTestCase):
    """Test cases for modules."""

    def setUp(self):
        """set up everything for a unit test."""
        super(ModulesTest, self).setUp()
        self.testmods = modules_tool()

    def init_testmods(self, test_modules_paths=None):
        """Initialize set of test modules for test."""
        if test_modules_paths is None:
            test_modules_paths = [os.path.abspath(os.path.join(os.path.dirname(__file__), 'modules'))]
        mod_paths = self.testmods.mod_paths[:]
        for path in test_modules_paths:
            self.testmods.prepend_module_path(path)
        for path in mod_paths:
            if path not in test_modules_paths:
                self.testmods.remove_module_path(path)

    # for Lmod, this test has to run first, to avoid that it fails;
    # no modules are found if another test ran before it, but using a (very) long module path works fine interactively
    def test_long_module_path(self):
        """Test dealing with a (very) long module path."""

        # create a really long modules install path
        tmpdir = tempfile.mkdtemp()
        long_mod_path = tmpdir
        subdir = 'foo'
        # Lmod v5.1.5 doesn't support module paths longer than 256 characters, so stay just under that magic limit
        while (len(os.path.abspath(long_mod_path)) + len(subdir)) < 240:
            long_mod_path = os.path.join(long_mod_path, subdir)

        # copy one of the test modules there
        gcc_mod_dir = os.path.join(long_mod_path, 'GCC')
        os.makedirs(gcc_mod_dir)
        gcc_mod_path = os.path.join(os.path.dirname(__file__), 'modules', 'GCC', '4.6.3')
        shutil.copy2(gcc_mod_path, gcc_mod_dir)

        # try and use long modules path
        self.init_testmods(test_modules_paths=[long_mod_path])
        ms = self.testmods.available()

        self.assertEqual(ms, ['GCC/4.6.3'])

        shutil.rmtree(tmpdir)

    def test_avail(self):
        """Test if getting a (restricted) list of available modules works."""
        self.init_testmods()

        # test modules include 3 GCC modules
        ms = self.testmods.available('GCC')
        self.assertEqual(ms, ['GCC/4.6.3', 'GCC/4.6.4', 'GCC/4.7.2'])

        # test modules include one GCC/4.6.3 module
        ms = self.testmods.available(mod_name='GCC/4.6.3')
        self.assertEqual(ms, ['GCC/4.6.3'])

        # all test modules are accounted for
        ms = self.testmods.available()
        self.assertEqual(len(ms), TEST_MODULES_COUNT)

    def test_exists(self):
        """Test if testing for module existence works."""
        self.init_testmods()
        self.assertTrue(self.testmods.exists('OpenMPI/1.6.4-GCC-4.6.4'))
        self.assertTrue(not self.testmods.exists(mod_name='foo/1.2.3'))
        # exists should not return True for incomplete module names
        self.assertFalse(self.testmods.exists('GCC'))

    def test_load(self):
        """ test if we load one module it is in the loaded_modules """
        self.init_testmods()
        ms = self.testmods.available()
        ms = [m for m in ms if not m.startswith('Core/') and not m.startswith('Compiler/')]

        for m in ms:
            self.testmods.load([m])
            self.assertTrue(m in self.testmods.loaded_modules())
            self.testmods.purge()

    def test_ld_library_path(self):
        """Make sure LD_LIBRARY_PATH is what it should be when loaded multiple modules."""
        self.init_testmods()

        testpath = '/this/is/just/a/test'
        os.environ['LD_LIBRARY_PATH'] = testpath

        # load module and check that previous LD_LIBRARY_PATH is still there, at the end
        self.testmods.load(['GCC/4.6.3'])
        self.assertTrue(re.search("%s$" % testpath, os.environ['LD_LIBRARY_PATH']))
        self.testmods.purge()

        # check that previous LD_LIBRARY_PATH is still there, at the end
        self.assertTrue(re.search("%s$" % testpath, os.environ['LD_LIBRARY_PATH']))
        self.testmods.purge()

    def test_purge(self):
        """Test if purging of modules works."""
        self.init_testmods()
        ms = self.testmods.available()

        self.testmods.load([ms[0]])
        self.assertTrue(len(self.testmods.loaded_modules()) > 0)

        self.testmods.purge()
        self.assertTrue(len(self.testmods.loaded_modules()) == 0)

        self.testmods.purge()
        self.assertTrue(len(self.testmods.loaded_modules()) == 0)

    def test_get_software_root_version_libdir(self):
        """Test get_software_X functions."""

        tmpdir = tempfile.mkdtemp()
        test_cases = [
            ('GCC', 'GCC'),
            ('grib_api', 'GRIB_API'),
            ('netCDF-C++', 'NETCDFMINCPLUSPLUS'),
            ('Score-P', 'SCOREMINP'),
        ]
        for (name, env_var_name) in test_cases:
            # mock stuff that get_software_X functions rely on
            root = os.path.join(tmpdir, name)
            os.makedirs(os.path.join(root, 'lib'))
            os.environ['EBROOT%s' % env_var_name] = root
            version = '0.0-%s' % root
            os.environ['EBVERSION%s' % env_var_name] = version

            self.assertEqual(get_software_root(name), root)
            self.assertEqual(get_software_version(name), version)
            self.assertEqual(get_software_libdir(name), 'lib')

            os.environ.pop('EBROOT%s' % env_var_name)
            os.environ.pop('EBVERSION%s' % env_var_name)

        # check expected result of get_software_libdir with multiple lib subdirs
        root = os.path.join(tmpdir, name)
        os.makedirs(os.path.join(root, 'lib64'))
        os.environ['EBROOT%s' % env_var_name] = root
        self.assertErrorRegex(EasyBuildError, "Multiple library subdirectories found.*", get_software_libdir, name)
        self.assertEqual(get_software_libdir(name, only_one=False), ['lib', 'lib64'])

        # only directories containing files in specified list should be retained
        open(os.path.join(root, 'lib64', 'foo'), 'w').write('foo')
        self.assertEqual(get_software_libdir(name, fs=['foo']), 'lib64')

        # clean up for previous tests
        os.environ.pop('EBROOT%s' % env_var_name)

        # if root/version for specified software package can not be found, these functions should return None
        self.assertEqual(get_software_root('foo'), None)
        self.assertEqual(get_software_version('foo'), None)
        self.assertEqual(get_software_libdir('foo'), None)

        # if no library subdir is found, get_software_libdir should return None
        os.environ['EBROOTFOO'] = tmpdir
        self.assertEqual(get_software_libdir('foo'), None)
        os.environ.pop('EBROOTFOO')

        shutil.rmtree(tmpdir)

    def test_wrong_modulepath(self):
        """Test whether modules tool can deal with a broken $MODULEPATH."""
        test_modules_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'modules')
        modules_test_installpath = os.path.join(self.test_installpath, 'modules', 'all')
        os.environ['MODULEPATH'] = "/some/non-existing/path:/this/doesnt/exists/anywhere:%s" % test_modules_path
        init_config()
        modtool = modules_tool()
        self.assertEqual(len(modtool.mod_paths), 2)
        self.assertTrue(os.path.samefile(modtool.mod_paths[0], modules_test_installpath))
        self.assertEqual(modtool.mod_paths[1], test_modules_path)
        self.assertTrue(len(modtool.available()) > 0)

def suite():
    """ returns all the testcases in this module """
    return TestLoader().loadTestsFromTestCase(ModulesTest)

if __name__ == '__main__':
    main()
