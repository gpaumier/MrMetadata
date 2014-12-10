#!/bin/bash
mysql --defaults-file=/data/project/mrmetadata/.my.cnf -h commonswiki.labsdb < /data/project/mrmetadata/commons_query.txt > /data/project/mrmetadata/commons_list.txt
sed -i.orig -e '1d' commons_list.txt
mysql --defaults-file=/data/project/mrmetadata/.my.cnf -h commonswiki.labsdb < /data/project/mrmetadata/commons_filecount_query.txt > /data/project/mrmetadata/commons_filecount.txt
