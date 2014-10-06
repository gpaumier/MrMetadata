 #!/usr/bin/python

import os
import io
import sys
import pywikibot
from pywikibot import pagegenerators
from pywikibot import site
from pywikibot import page
from pywikibot import config2
import json
import time
import jinja2
import datetime
import argparse
import collections


SEP = '\n_________________________________\n\n'

template_loader = jinja2.FileSystemLoader( searchpath="templates/" )

template_env = jinja2.Environment( loader=template_loader )

config2.register_families_folder('families')

#--------------------------------------------------------------------------------
#                                      main
#--------------------------------------------------------------------------------

def main(args):
    
    if (args.family and args.prefix):
       check_local_uploads(args.family, args.prefix)
       return
    
    if args.commons:
        check_commons()
        return
    
    json_list = args.json
    
    resume = args.resume
    
    if not json_list:
        json_list = 'sites_with_local_uploads.json'

    cycle_through_wikis(json_list, resume)
    
    
#--------------------------------------------------------------------------------
#                         get files and check metadata
#--------------------------------------------------------------------------------


def check_commons():
    
    print u'In the future, we\'ll be checking Commons here.'
    
    return


def cycle_through_wikis(json_list, resume):

    with open(json_list, 'r') as sites_with_local_uploads:
    
        wikis = json.load(sites_with_local_uploads)
        print SEP+u'Loaded wikis from JSON'+SEP
        
        wikis = collections.OrderedDict(sorted(wikis.items(), key=lambda t: t[0]))      # Make sure our dict is always in the same order

        if resume:
            resume_from = get_resume_point(json_list)
            
        for family in wikis:
            
            if resume and (family <> resume_from['family']):
                pass
            else:
                for prefix in wikis[family]:
                    if resume and (prefix <> resume_from['prefix']):
                        pass
                    else:
                        print u'Started run through {0}'.format(family)
                        
                        check_local_uploads(family, prefix)
                        set_resume_point(json_list, family, prefix)
                        resume = False
            
            

def check_local_uploads(family, prefix):
            
    print SEP+u'Started run through {0}.{1}'.format(prefix, family)

    output_directory = 'public_html/'+family+'/'+prefix
    if not os.path.exists(output_directory):      # Create language directory if it doesn't exist
        os.makedirs(output_directory)

    site_tally = {  'prefix': prefix,
                    'family': family,
                    'number_of_files': 0,
                    'number_of_files_with_missing_mrd': 0,
                    'percentage_ok': 0,
                    'last_updated_on': None
                    }

    start_checking_site = time.clock()
            
    REQUEST_FILES_BY_BATCHES_OF = 3000
            
    API_STEP = 200

    CHECK_FILES_BY_BATCHES_OF = 50 # Max value is 50

    NUMBER_OF_FILES_PER_PAGE = 500

    current_site = pywikibot.getSite(prefix, family)

    start = '!'

    batch_of_files = get_batch_of_files(current_site, REQUEST_FILES_BY_BATCHES_OF, API_STEP, start)
            
    files_with_missing_mrd = []

    page_number = 1

    files_to_print_on_the_first_page = {}

    all_files_are_on_first_page = True

    while len(batch_of_files):

        site_tally['number_of_files'] = site_tally['number_of_files'] + len(batch_of_files)


        # Is there another batch after that? If so, save where to start it

        another_batch_is_coming = len(batch_of_files) == REQUEST_FILES_BY_BATCHES_OF

        if ( another_batch_is_coming ):
            start = batch_of_files[-1].title(withNamespace = False).encode('utf-8')
            #print u'Next batch will start at {0}'.format(start) #debug
                    
            batch_of_files = batch_of_files[:-1]

        # Check the files in our batch for machine-readable metadata

        while len(batch_of_files):
            files_with_missing_mrd = files_with_missing_mrd + check_metadata(current_site, batch_of_files[:CHECK_FILES_BY_BATCHES_OF])
            batch_of_files = batch_of_files[CHECK_FILES_BY_BATCHES_OF:]

        site_tally['number_of_files_with_missing_mrd'] = len(files_with_missing_mrd) + site_tally['number_of_files_with_missing_mrd']


        # Output pages if we have enough files to list

        while (len(files_with_missing_mrd) >= NUMBER_OF_FILES_PER_PAGE):

            # We take the first page out to print it at the end (so we have can display the tally)

            if not len(files_to_print_on_the_first_page):
                files_to_print_on_the_first_page = list(files_with_missing_mrd[:NUMBER_OF_FILES_PER_PAGE])

            else:

            # We've got enough files to print a page; print them and remove them from the queue

                output_site_page(output_directory, page_number, current_site, files_with_missing_mrd[:NUMBER_OF_FILES_PER_PAGE], NUMBER_OF_FILES_PER_PAGE )
                    
            page_number = page_number + 1

            files_with_missing_mrd = files_with_missing_mrd[NUMBER_OF_FILES_PER_PAGE:]
                    
            if len(files_with_missing_mrd):
                all_files_are_on_first_page = False

        # If we haven't had enough to fill several pages, add what we have to the first page
                
        if not len(files_to_print_on_the_first_page):
            files_to_print_on_the_first_page = list(files_with_missing_mrd[:NUMBER_OF_FILES_PER_PAGE])


        # We're done with this batch, request another one
                
        if ( another_batch_is_coming ):
            batch_of_files = get_batch_of_files(current_site, REQUEST_FILES_BY_BATCHES_OF, API_STEP, start)
                    
        else:
            # If we're still on the first page, dump all the remaining files there

            if not len(files_to_print_on_the_first_page):
                files_to_print_on_the_first_page = list(files_with_missing_mrd[:NUMBER_OF_FILES_PER_PAGE])

    # Print the last page, if it's not the first page

    if len(files_with_missing_mrd) and not all_files_are_on_first_page:

        output_site_page(output_directory, page_number, current_site, files_with_missing_mrd, NUMBER_OF_FILES_PER_PAGE, last_page = True )


    done_checking_site = time.clock();
    print u'Checked {0}.{1} in {2}s'.format(prefix, family, done_checking_site - start_checking_site)


    # Update the tallies
            
    try:
        site_tally['percentage_ok'] = int( 100 - ( site_tally['number_of_files_with_missing_mrd'] * 100 
                                        / site_tally['number_of_files']) )
    except ZeroDivisionError:
        site_tally['percentage_ok'] = 100           # No files on the wiki means there's nothing to fix
            
    site_tally['last_updated_on'] = datetime.date.today().isoformat()

    update_tallies( site_tally )

    # Print the first page now that we have the tallies

    output_first_page(output_directory, current_site, files_to_print_on_the_first_page, NUMBER_OF_FILES_PER_PAGE, site_tally, last_page = all_files_are_on_first_page  )

            
    update_main_page()                  # Update with numbers from the latest wiki that was checked


def get_batch_of_files(current_site, batches_of, api_step, start_from):

    start_getting_allfiles = time.clock()

    #print u'Requesting {0} files'.format(batches_of) #debug

    batch_of_files_generator = pagegenerators.AllpagesPageGenerator(site=current_site, start=start_from, namespace=6, includeredirects=False, total=batches_of, step=api_step, content=False)

    done_getting_allfiles = time.clock();
                            
    batch_of_files=[]

    for page in batch_of_files_generator:
        batch_of_files.append(page)
                    
    #print u'Got {0} pages in {1}s'.format(len(batch_of_files), done_getting_allfiles - start_getting_allfiles) #debug

    return batch_of_files



def check_metadata(current_site, pages):
    
    start_checking_metadata = time.clock()
    number_of_pages_to_check = len(pages)
    #print u'Checking metadata for {0} pages'.format(number_of_pages_to_check) #debug

    titles = []
    files_with_missing_mrd = []
    
    for i in range(0, number_of_pages_to_check):
        titles.append(pages[i].title(withSection=False))
    
    args = {"titles": titles}
    args["total"] = number_of_pages_to_check
    query = current_site._generator(site.api.PropertyGenerator,
                                type_arg="imageinfo",
                                iiprop=["extmetadata"],
                                **args)
    
    for page in query:
        
        no_mr_description = no_mr_author = no_mr_source = no_mr_license_short = no_mr_license_url = False

        title = page['title']
        
        try:
            metadata = page['imageinfo'][0]['extmetadata']
            # print u'checking metadata for "{0}"'.format(title) # for debugging
            
            try:
                mr_description = metadata['ImageDescription']['value']
            except KeyError:
                no_mr_description = True

            try:
                mr_author = metadata['Artist']['value']
            except KeyError:
                no_mr_author = True

            try:
                mr_source = metadata['Credit']['value']
            except KeyError:
                no_mr_source = True
                    
            try:
                mr_license_short = metadata['LicenseShortName']['value']
            except KeyError:
                no_mr_license_short = True
                    
            try:
                mr_license_url = metadata['LicenseUrl']['value']
            except KeyError:
                no_mr_license_url = True
                
            if ( no_mr_description or no_mr_author or no_mr_source or no_mr_license_short or no_mr_license_url):
                files_with_missing_mrd.append([title, no_mr_description, no_mr_author, no_mr_source, no_mr_license_short, no_mr_license_url])
                        
        except KeyError: #No imageinfo means no image, so skip
            #print u'Skipping {0}'.format(title)
            pass
                        
    done_checking_metadata = time.clock();
    #print u'Metadata checked in {0}s'.format(done_checking_metadata - start_checking_metadata)

    return files_with_missing_mrd    



#--------------------------------------------------------------------------------
#                              Update tallies
#--------------------------------------------------------------------------------


def update_tallies( site_tally ):

    #TODO handle case where there are no more files on the wiki

    #Reminder: site_tally = {'prefix', 'family', 'number_of_files', 'number_of_files_with_missing_mrd', 'percentage_ok', 'last_updated_on'}
    
    family = site_tally.pop('family')       # get those values and remove them to save time when we save the rest later
    prefix = site_tally.pop('prefix')
    timestamp = site_tally.pop('last_updated_on')
    
    if not os.path.exists('tallies.json'):
        tallies = {}
    else:
        with io.open('tallies.json', 'r', encoding='utf8') as tallies_file:
            tallies = json.load(tallies_file)
            tallies_file.close()


    # Get the existing site tally if they exist, else initialize them
    
    try:
        old_site_tally_timestamp = tallies[family][prefix]['last_updated_on']
        old_site_tally = tallies[family][prefix][old_site_tally_timestamp]
    except KeyError:
        old_site_tally = {  'number_of_files': 0,
                            'number_of_files_with_missing_mrd': 0}

    # Get the existing global tallies if they exist, else initialize them
        
    try:
        last_global_tally_timestamp = tallies['global']['global']['last_updated_on']
        global_tally = tallies['global']['global'][last_global_tally_timestamp]
    except KeyError:
        global_tally = { 'number_of_files': 0, 'number_of_files_with_missing_mrd': 0 }
        
    try:
        last_family_tally_timestamp = tallies['global'][family]['last_updated_on']
        family_tally = tallies['global'][family][last_family_tally_timestamp]
    except KeyError:
        family_tally = { 'number_of_files': 0, 'number_of_files_with_missing_mrd': 0}
                
                
    # Update the family tally
        
    family_tally['number_of_files'] = family_tally['number_of_files'] - old_site_tally['number_of_files'] + site_tally['number_of_files']
       
    family_tally['number_of_files_with_missing_mrd'] = family_tally['number_of_files_with_missing_mrd'] - old_site_tally['number_of_files_with_missing_mrd'] + site_tally['number_of_files_with_missing_mrd']
            
    try:
        family_tally['percentage_ok'] =  int(100 - ( 100 * family_tally['number_of_files_with_missing_mrd'] / family_tally['number_of_files'] ))
    except ZeroDivisionError:                       # No files on a family
        site_tally['percentage_ok'] = 100           # Probably not gonna happen but let's be safe
        
    # Update the global tally
        
    global_tally['number_of_files'] = global_tally['number_of_files'] - old_site_tally['number_of_files'] + site_tally['number_of_files']
        
    global_tally['number_of_files_with_missing_mrd'] = global_tally['number_of_files_with_missing_mrd'] - old_site_tally['number_of_files_with_missing_mrd'] + site_tally['number_of_files_with_missing_mrd']
                
    global_tally['percentage_ok'] =  int(100 - ( 100 * global_tally['number_of_files_with_missing_mrd'] / global_tally['number_of_files'] ))
    
    # Prepare the site tally for writing

    try:
        tallies[family][prefix]['last_updated_on'] = timestamp
        
    except KeyError:                                    # No tally yet for this family or this wiki
        
        try:
            tallies[family] = { prefix: {} }
            tallies[family][prefix]['last_updated_on'] = timestamp

        except KeyError:                                # No tally yet for this family
            tallies = { family: { prefix: {} } }
            tallies[family][prefix]['last_updated_on'] = timestamp
            
    tallies[family][prefix][timestamp] = site_tally
            
    # Prepare the global tally for writing
    
    try:
        tallies['global']['global']['last_updated_on'] = timestamp
    except KeyError:                                    # No global tallies
        tallies['global'] = { 'global': { 'last_updated_on': timestamp } }
    
    tallies['global']['global'][timestamp] = global_tally
    
    # Prepare the family tally for writing
    
    try:
        tallies['global'][family]['last_updated_on'] = timestamp
    except KeyError:                                    # No global tally for this tamily
        tallies['global'][family] = { 'last_updated_on': timestamp }
        
    tallies['global'][family][timestamp] = family_tally

    # Write the updated tallies to the JSON file

    with io.open('tallies.json', 'w', encoding='utf8') as tallies_file:
                
        tallies_file.write(unicode(json.dumps(tallies,indent=4,sort_keys=True,ensure_ascii=False)))
              
        tallies_file.truncate()
        tallies_file.close()

    print u'Updated tallies.'


     
#--------------------------------------------------------------------------------
#                              Resume a check (JSON only)
#--------------------------------------------------------------------------------

def get_resume_point(json_list):
    
    with io.open('resume_'+json_list, 'r', encoding='utf8') as resume_file:
        resume_point = json.load(resume_file)
        resume_file.close()
        
    return resume_point



def set_resume_point(json_list, family, prefix):
    
    resume_point = {'family': family, 'prefix': prefix}
    
    with io.open('resume_'+json_list, 'w', encoding='utf8') as resume_file:       
        resume_file.write(unicode(json.dumps(resume_point,indent=4,sort_keys=True,ensure_ascii=False)))
        resume_file.close()


#--------------------------------------------------------------------------------
#                              Output HTML pages
#--------------------------------------------------------------------------------


def update_main_page():
    
    template = template_env.get_template( 'main.html' )
    
    tallies = {}

    with io.open('tallies.json', 'r', encoding='utf8') as tallies_file:
        unsorted_tallies = json.load(tallies_file)
        tallies_file.close()

    global_tally = unsorted_tallies['global'].pop('global')         # Get all tallies
    global_tally = global_tally[ global_tally['last_updated_on'] ]  # Get latest tally
        
    family_tallies = unsorted_tallies.pop('global')
        
    alphabetical_tallies = collections.OrderedDict(sorted(unsorted_tallies.items(), key=lambda t: t[0]))

    for family in alphabetical_tallies:
        alphabetical_tallies[family] = collections.OrderedDict(sorted(alphabetical_tallies[family].items(), key=lambda t: t[0]))    
        
    template_params = { 'global': global_tally,
                        'family_tallies': family_tallies,
                        'site_tallies': alphabetical_tallies
                        }

    html_output = template.render( template_params )

    file_name = 'public_html/index.html'

    with io.open(file_name, 'w', encoding='utf8') as f:
        f.write(html_output)
        f.close()




def format_files ( files_to_print, current_site ):

    MR_MISSING = '<td class="danger">missing</td>'
    MR_OK = '<td class="success">ok</td>'

    formatted_files_to_print = []
    item_index = 1

    for item in files_to_print:

        file_title = item[0]
        page = pywikibot.Page(source = current_site, title = file_title, ns = 6)
        url = 'https://' + current_site.hostname() + '/wiki/' + page.title(asUrl=True)

        formatted_files_to_print.append({'index': item_index,
            'title': file_title,
            'url': url,
            'description': MR_MISSING if item[1] else MR_OK,
            'author': MR_MISSING if item[2] else MR_OK,
            'source': MR_MISSING if item[3] else MR_OK,
            'license_short': MR_MISSING if item[4] else MR_OK,
            'license_url': MR_MISSING if item[5] else MR_OK})
        
        item_index = item_index + 1

    return formatted_files_to_print


def output_site_page(output_directory, page_number, current_site, files_to_print, max_files_per_page, last_page = False, ):

    template = template_env.get_template( 'site_page.html' )

    formatted_list_of_files = format_files ( files_to_print, current_site)
        
    pages = {   'number': page_number,
                'previous': 'index' if (page_number == 2) else str(page_number - 1).zfill(5),
                'next': str(page_number + 1).zfill(5),
                'is_last': last_page,
            }
    
    template_params = { 'site' : str(current_site.sitename()),
                    'pages': pages,
                    'max_files_per_page': max_files_per_page,
                    'formatted_list_of_files' : formatted_list_of_files,
                    'return_to_root' : '../../'}

    html_output = template.render( template_params )

    file_name = output_directory + '/' + str(page_number).zfill(5) + '.html'

    with io.open(file_name, 'w', encoding='utf8') as f:
        f.write(html_output)
        f.close()


def output_first_page(output_directory, current_site, files_to_print, max_files_per_page, tallies, last_page = False, ):

    template = template_env.get_template( 'site_page.html' )

    formatted_list_of_files = format_files ( files_to_print, current_site)
    
    pages = {   'number': 1,
                'previous': '0',
                'next': str(2).zfill(5),
                'is_last': last_page,
            }

    template_params = { 'site' : str(current_site.sitename()),
                    'pages': pages,
                    'max_files_per_page': max_files_per_page,
                    'formatted_list_of_files' : formatted_list_of_files,
                    'tallies': tallies,
                    'return_to_root' : '../../'}

    html_output = template.render( template_params )

    file_name = output_directory + '/index.html'

    with io.open(file_name, 'w', encoding='utf8') as f:
        f.write(html_output)
        f.close()



def format_number ( number ):
    return '    {:,}'.format( number )


template_env.filters['format_number'] = format_number


#--------------------------------------------------------------------------------

if __name__ == '__main__':
    
    parser = argparse.ArgumentParser(description=u'Go through a wiki or a set of wikis and identify files missing machine-readable metadata')
    
    parser.add_argument('--family', help=u'the family of the wiki to check')
    
    parser.add_argument('--prefix', help=u'the prefix of the wiki to check')
    
    parser.add_argument('--commons', action='store_const', const=True, help=u'check Commons')
    
    parser.add_argument('--json', help=u'A JSON file containing a list of wikis to check')
    
    parser.add_argument('--resume', action='store_const', const=True, help=u'Resume a check from a JSON file from the last wiki completed')
    
    arguments = parser.parse_args()
    
    try:
        main(arguments)
       
    finally:
        pywikibot.stopme()