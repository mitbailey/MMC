#
# @file mcpherson.py
# @author Mit Bailey (mitbailey@outlook.com)
# @brief McPherson monochromator instrument geometric constants database.
# @version See Git tags for version information.
# @date 2023.02.10
# 
# @copyright Copyright (c) 2023
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
#

class McPherson:
    MONO_MODELS = [
        'Monarch',
        'Monarch (w/ 789)',

        '272',
        
        '225',
        '241',
        '2253M5',

        'XCT',

        '302(1)',
        '270(2)',

        '608 Pre-Disperser',

        '248',
        '310G(3)',

        '247',

        'Motorized slit',

        '205 S/N 100+',
        '207 S/N 100+',
        '209 S/N 100+',
        '216.5 S/N 100+',
        '218 S/N 100+',
        '219 S/N 100+',
        '213 S/N 100+',
        '235 S/N 100+',
        '2051 S/N 100+',
        '2061 S/N 100+',
        '2062 S/N 100+',
        '2062M3 S/N 100+',

        '205 S/N 99-',
        '207 S/N 99-',
        '209 S/N 99-',
        '216.5 S/N 99-',
        '218 S/N 99-',
        '219 S/N 99-',
        '213 S/N 99-',
        '235 S/N 99-',
        '2051 S/N 99-',
        '2061 S/N 99-',
        '2062 S/N 99-',
        '2062M3 S/N 99-',

        '2062M3 S/N 310+',

        '2062M3 S/N 309-',
        '275D',
        '275',
    ]

    MONO_GEO_CONST = {
        'Monarch': (1200*(5000/8889)),
        'Monarch (w/ 789)': (1200*(5000/8889)),

        '272': None,
        
        '225': 3000,
        '241': 3000,
        '2253M5': 3000,

        'XCT': 1200,

        '302(1)': 2400,
        '270(2)': 2400,

        '608 Pre-Disperser': None,

        '248': None,
        '310G(3)': None,

        '247': None,

        'Motorized slit': None,

        '205 S/N 100+': 4800,
        '207 S/N 100+': 4800,
        '209 S/N 100+': 4800,
        '216.5 S/N 100+': 4800,
        '218 S/N 100+': 4800,
        '219 S/N 100+': 4800,
        '213 S/N 100+': 4800,
        '235 S/N 100+': 4800,
        '2051 S/N 100+': 4800,
        '2061 S/N 100+': 4800,
        '2062 S/N 100+': 4800,
        '2062M3 S/N 100+': 4800,

        '205 S/N 99-': 6000,
        '207 S/N 99-': 6000,
        '209 S/N 99-': 6000,
        '216.5 S/N 99-': 6000,
        '218 S/N 99-': 6000,
        '219 S/N 99-': 6000,
        '213 S/N 99-': 6000,
        '235 S/N 99-': 6000,
        '2051 S/N 99-': 6000,
        '2061 S/N 99-': 6000,
        '2062 S/N 99-': 6000,
        '2062M3 S/N 99-': 6000,

        '2062M3 S/N 310+': 15000,

        '2062M3 S/N 309-': 12000,
        '275D': 12000,
        '275': 12000,
    }

    MONO_STEPS_PER_REV = {
        'Monarch': 49152,
        'Monarch (w/ 789)': 5353.1,

        '272': 18000,
        
        '225': 18000,
        '241': 18000,
        '2253M5': 18000,

        'XCT': 18000,

        '302(1)': 18000,
        '270(2)': 18000,

        '608 Pre-Disperser': 18000,

        '248': 18000,
        '310G(3)': 18000,

        '247': 18000,

        'Motorized slit': 18000,

        '205 S/N 100+': 18000,
        '207 S/N 100+': 18000,
        '209 S/N 100+': 18000,
        '216.5 S/N 100+': 18000,
        '218 S/N 100+': 18000,
        '219 S/N 100+': 18000,
        '213 S/N 100+': 18000,
        '235 S/N 100+': 18000,
        '2051 S/N 100+': 18000,
        '2061 S/N 100+': 18000,
        '2062 S/N 100+': 18000,
        '2062M3 S/N 100+': 18000,

        '205 S/N 99-': 18000,
        '207 S/N 99-': 18000,
        '209 S/N 99-': 18000,
        '216.5 S/N 99-': 18000,
        '218 S/N 99-': 18000,
        '219 S/N 99-': 18000,
        '213 S/N 99-': 18000,
        '235 S/N 99-': 18000,
        '2051 S/N 99-': 18000,
        '2061 S/N 99-': 18000,
        '2062 S/N 99-': 18000,
        '2062M3 S/N 99-': 18000,

        '2062M3 S/N 310+': 18000,

        '2062M3 S/N 309-': 18000,
        '275D': 18000,
        '275': 18000,
    }

    MONO_DIRECT_NM_REV = {
        '272': {570: 12.5, 1140: 25, 1710: 37.5, 2280: 50},
        
        '608 Pre-Disperser': 10,

        '248': None, # 0.1 inch ???
        '310G(3)': None, # 0.1 inch ???

        '247': None, # 0.025 inch ???

        'Motorized slit': None, # 250 micrometer ???
    }

    def get_steps_per_nm(steps_per_rev: float, model: str, grating_density: float = 0):
        GEO = McPherson.MONO_GEO_CONST[model]

        if GEO is None:
            if model == '272':
                try:
                    DIR = McPherson.MONO_DIRECT_NM_REV[model][grating_density]
                except Exception as e:
                    raise RuntimeError('Model', model, 'is not supported or is not supported with a grating density of', grating_density, 'grooves per millimeter.')
            else:
                DIR = McPherson.MONO_DIRECT_NM_REV[model]
            if DIR is None:
                raise RuntimeError('Model', model, 'is not supported or is not supported with a grating density of', grating_density, 'grooves per millimeter.')
            return steps_per_rev / DIR

        return (steps_per_rev * grating_density) / GEO
