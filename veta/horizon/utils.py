# Copyright 2013 GridCentric Inc.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

def epoch_to_seconds(e):
    e = e.lower()
    units = { '^(\d+)w$' : (60 * 60 * 24 * 7),
              '^(\d+)d$' : (60 * 60 * 24),
              '^(\d+)h$' : (60 * 60),
              '^(\d+)m$' : (60),
              '^(\d+)s$' : 1,
              '^(\d+)$' : 1 }
    for (pattern, factor) in units.items():
        m = re.match(pattern, e)
        if m is not None:
            val = long(m.group(1))
            seconds = val * factor
            return seconds
    raise ValueError('Invalid epoch %s.' % e)

def seconds_to_epoch(s):
    factors = [
        ((60 * 60 * 24 * 7), "week"),
        ((60 * 60 * 24), "day"),
        ((60 * 60), "hour"),
        ((60), "minute"),
        ((1), "second") # Catch-all
    ]

    for (factor, epoch) in factors:
        if s % factor == 0:
            count = s / factor
            if count > 1:
                return "%d %ss" % (count, epoch)
            else:
                return "%s" % (epoch)

def schedule_to_str(freq, ret):
    return "Every %s for the last %s" % (seconds_to_epoch(freq),
                                         seconds_to_epoch(ret))
