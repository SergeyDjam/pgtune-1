#!/usr/bin/env python2.7
# encoding: utf-8

'''
pgtune -- postgresql.conf tuner

See README.md.
'''

from __future__ import print_function
import argparse
import collections
import math
import os

B, K, M, G = (1024**i for i in range(4))

settings = {
'mem_total': os.sysconf('SC_PAGE_SIZE') * os.sysconf('SC_PHYS_PAGES'),  # bytes
'autovacuum_max_workers': 3  # default in postgresql.conf
}


def format_bytes(n):

    units = ('', 'kB', 'MB', 'GB')  # Restricted per section 18.1.1 in v9.2.
    base = 1024
    decrement_threshold = 0.2  # experimental
    divisor_max = len(units) - 1

    exponent = math.log(n, base) if n > 0 else 0
    remainder = exponent % 1
    exponent = int(exponent)  # implicit floor

    decrement = int(0 < remainder < decrement_threshold)
    divisor = max(0, exponent - decrement)
    divisor = min(divisor, divisor_max)

    quotient = int(n/(base**divisor))  # implicit floor
    unit = units[divisor]
    return "{}{}".format(quotient, unit)


def parse_args():

    parser = argparse.ArgumentParser(description='postgresql.conf tuner')

    parser.add_argument('-c', '--max_connections', dest='max_connections',
                        type=lambda s: max(1, int(s)),
                        default=100,
                        help='minimally necessary maximum connections '
                             '(default: %(default)s) (min: 1)')

    mem_str = format_bytes(settings['mem_total'])
    parser.add_argument('-f', '--mem_fraction', dest='mem_fraction',
                        type=lambda s: max(0, float(s)),
                        default=1.0,
                        help=('fraction (>0 to 1.0) of total physical memory '
                              '({}) to consider '
                              '(default: %(default)s)').format(mem_str))

    args = parser.parse_args()
    for k, v in args._get_kwargs():
        settings[k] = v

    settings['mem_fractional'] = int(settings['mem_total'] *
                                     settings['mem_fraction']
                                     )  # implicit floor


def tune_conf():

    m = settings['mem_fractional']
    conf = c = collections.OrderedDict()
    fb = format_bytes

    c['max_connections'] = settings['max_connections']

    c['shared_buffers'] = fb(m*.25)  # Not restricted to 8G.
    effective_cache_size = m*.625
    c['effective_cache_size'] = fb(effective_cache_size)
    c['work_mem'] = fb(effective_cache_size /
                       (settings['max_connections'] * 2  # x by active tables
                        + settings['autovacuum_max_workers']))
    c['maintenance_work_mem'] = fb((m*.25) /  # Not restricted.
                                   (settings['autovacuum_max_workers'] + 2))

    return conf


def print_conf(conf):

    print('# pgtune configuration for connections={} and memory={}.\n'
          .format(settings['max_connections'],
                  format_bytes(settings['mem_fractional'])))

    for i in conf.items():
        print('{} = {}'.format(*i))


def main():

    parse_args()
    conf = tune_conf()
    print_conf(conf)


if __name__ == "__main__":
    main()
