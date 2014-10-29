 #!/usr/bin/python

import os
import io
import sys
import json
import time
import jinja2
import datetime
import collections


template_loader = jinja2.FileSystemLoader( searchpath="templates/" )

template_env = jinja2.Environment( loader=template_loader )

#--------------------------------------------------------------------------------
#                                      main
#--------------------------------------------------------------------------------

def main():
    
    with open('all_sites_with_local_uploads.json', 'r') as sites_with_local_uploads:
        
        wikis = json.load(sites_with_local_uploads)
        sites_with_local_uploads.close()
            
    wikis = collections.OrderedDict(sorted(wikis.items(), key=lambda t: t[0])) 
    
    formatted_test_results = run_tests(wikis)
    
    output_tests_page(formatted_test_results)
    

def run_tests(wikis):
    
    TEST_FAILED_CLASS = 'danger'
    TEST_PASSED_CLASS = 'success'
    table_content = ''
    
    with open('tallies.json', 'r') as tallies_file:
        
        tallies = json.load(tallies_file)
        tallies_file.close()

    for family in wikis:
        
        for prefix in wikis[family]:
                       
            try:
                
                # Test that the tallies for this wiki was updated less than 2 days ago
                
                last_updated_on_date = datetime.datetime.strptime(tallies[family][prefix]['last_updated_on'], '%Y-%m-%d').date()
                
                time_difference = datetime.date.today() - last_updated_on_date
                
                if ( time_difference.days < 2 ):
                    test_result_class = TEST_PASSED_CLASS
                else:
                    test_result_class = TEST_FAILED_CLASS
                
                time_test_cell = '<td class="{0} text-center">{1}</td>'.format(test_result_class, tallies[family][prefix]['last_updated_on'])
                
                # Test that we don't have more files with missing machine-readable data
                # than we have files overall
                
                totals_difference = tallies[family][prefix]['number_of_files'] - tallies[family][prefix]['number_of_files_with_missing_mrd']
                
                if ( totals_difference >= 0 ):
                    test_result_class = TEST_PASSED_CLASS
                else:
                    test_result_class = TEST_FAILED_CLASS
                
                totals_test_cell = '<td class="{0} text-center">{1}</td>'.format(test_result_class, totals_difference)
        
                # Format the wiki's line in the dashboard's table
                
                line = '<tr><td>{0}</td><td>{1}</td>{2}{3}</tr>'.format(family, prefix, time_test_cell, totals_test_cell)
    
            except KeyError:    # We didn't find that wiki
                
                line = '<tr><td>{0}</td><td>{1}</td><td class="{2} text-center" colspan="2">no information</td></tr>'.format(family, prefix, TEST_FAILED_CLASS)
     
            table_content = table_content + '\n' + line
            
    return table_content

#--------------------------------------------------------------------------------
#                              Output HTML pages
#--------------------------------------------------------------------------------


def output_tests_page(formatted_test_results):
    
    template = template_env.get_template( 'tests_page.html' )
        
    template_params = { 'formatted_test_results': formatted_test_results }

    html_output = template.render( template_params )

    file_name = 'public_html/tests.html'

    with io.open(file_name, 'w', encoding='utf8') as f:
        f.write(html_output)
        f.close()



#--------------------------------------------------------------------------------

if __name__ == '__main__':
    
    try:
        main()
       
    finally:
        pywikibot.stopme()