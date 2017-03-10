# cg-stat-collector

Yet another OS statistics collector with support for

- ps and cgroups as sources
- syslog and elasticsearch as data storage

## usage

usage: cg-stat-collector [-h] [--source SOURCE] [--target TARGET]
                         [--interval [INTERVAL]]

System Metric Collector

optional arguments:
  -h, --help            show this help message and exit
  --source SOURCE       add a metric source. Following are available
                          - console
                          - unixps
                          - linuxps
                          - cgroupfs,PATH_TO_CGROUPFS
  --target TARGET       add a logging target. Following are available
                          - syslog
                          - netsyslog,(tcp|udp)://HOST:PORT
                          - elasticsearch,HOST:PORT
  --interval [INTERVAL]
                        interval between metric collection runs

Example:

  Run collector every minute and collect cgroup and ps data. Send it to syslog.

  cg-stat-collector.py \
	--interval 60 \
	--source cgroupfs,/sys/fs/cgroup \
	--source linuxps \
	--target syslog
 
