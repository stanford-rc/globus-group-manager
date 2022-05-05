# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et

# This file lets a user access via `python -m ggm …`.
# All it does is call out to the CLI's main(), which takes things from there.

# © 2022, The Board of Trustees of the Leland Stanford Junior University.
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from ggm.cli import main

if __name__ == '__main__':
    main()
