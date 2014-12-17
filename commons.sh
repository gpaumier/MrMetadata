#!/bin/bash
mysql --defaults-file=/data/project/mrmetadata/.my.cnf -h commonswiki.labsdb < /data/project/mrmetadata/commons_query.txt > /data/project/mrmetadata/commons_list.txt
sed -i.orig -e '1d' commons_list.txt
mysql --defaults-file=/data/project/mrmetadata/.my.cnf -h commonswiki.labsdb < /data/project/mrmetadata/commons_filecount_query.txt > /data/project/mrmetadata/commons_filecount.txt
/data/project/mrmetadata/bin/python mrmetadata.py --commons
mysql --defaults-file=/data/project/mrmetadata/.my.cnf -h commonswiki.labsdb < /data/project/mrmetadata/commons_noinfo_users_query.txt > /data/project/mrmetadata/public_html/commons/commons/commons_noinfo_users_results.txt