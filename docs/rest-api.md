STRING API
STRING has an application programming interface (API) which enables you to get the data without using the graphical user interface of the web page. The API is convenient if you need to programmatically access some information but still do not want to download the entire dataset. There are several scenarios when it is practical to use it. For example, you might need to access some interaction from your own scripts or want to incorporate STRING network in your web page.

We currently provide an implementation using HTTP, where the database information is accessed by HTTP requests. Due to implementation reasons, similarly to the web site, some API methods will allow only a limited number of proteins in each query. If you need access to the bulk data, you can download the entire dataset from the download page

There are several methods available through STRING API:

Method	API method URL	Description
Mapping identifiers	/api/tsv/get_string_ids?	Maps common protein names, synonyms and UniProt identifiers into STRING identifiers
Getting the network image	/api/image/network?	Retrieves the network image with your input protein(s) highlighted in color
Linking to the network on STRING webpage	/api/tsv/get_link?	Get the link to STRING webpage showing your network
Linking to STRING search results	/cgi/network/identifiers?	Create the link to the search results page
Embedding interactive network in the website	javascript:getSTRING(...)	A call that lets you embed a network with movable bubbles and protein information pop-ups in a website.
Retrieving the interaction network	/api/tsv/network?	Retrieves the network interactions for your input protein(s) in various text based formats
Getting the interaction partners	/api/tsv/interaction_partners?	Gets all the STRING interaction partners of your proteins
Getting protein similarity scores	/api/tsv/homology?	Retrieve the protein similarity scores between the input proteins
Retrieving best similarity hits between species	/api/tsv/homology_best?	Retrieve the similarity from your input protein(s) to the best (most) similar protein from each STRING species.
Performing functional enrichment	/api/tsv/enrichment?	Performs the enrichment analysis of your set of proteins for the Gene Ontology, KEGG pathways, UniProt Keywords, PubMed publications, Pfam, InterPro and SMART domains.
Retrieving functional annotation	/api/tsv/functional_annotation?	Gets the functional annotation (Gene Ontology, UniProt Keywords, PFAM, INTERPRO and SMART domains) of your list of proteins.
Retrieving enrichment figure	/api/image/enrichmentfigure?	Generates the enrichment figure for a specific category.
Performing interaction enrichment	/api/tsv/ppi_enrichment?	Tests if your network has more interactions than expected
Values/Ranks enrichment analysis	/api/tsv/valuesranks_enrichment_submit?	Perform enrichment analysis given the data from your full experiment
Getting current STRING version	/api/tsv/version	Prints the current STRING version and its stable address
Getting startedTop ↑
As STRING API works like normal HTTP request you can access it like any other webpage. Just copy/paste the following URL into your browser to get the PNG image of Patched 1 gene network.

https://string-db.org/api/image/network?identifiers=PTCH1
However most likely you will be accessing the API from your scripts or website. Examples of python scripts for each of the API calls are attached at the end of each section.

In order to query with more than one identifier in one call just separate each identifier by carriage return character "\r" or "%0d" (depending how you call STRING):

https://string-db.org/api/image/network?identifiers=PTCH1%0dSHH%0dGLI1%0dSMO%0dGLI3
or from python3:

import requests ## python -m pip install requests
response = requests.get("https://string-db.org/api/image/network?identifiers=PTCH1%0dSHH%0dGLI1%0dSMO%0dGLI3")
with open('string_network.png', 'wb') as fh:
    fh.write(response.content)
...but before you start coding:
Please be considerate and wait one second between each call, so that our server won't get overloaded.
Although STRING understands a variety of identifiers and does its best to disambiguate your input it is recommeded to map your identifier first (see: mapping). Querying the API with a disambiguated identifier (for example 9606.ENSP00000269305 for human TP53) will guarantee much faster server response.
Another way to guarantee faster server response is to specify from which species your proteins come from (see 'species' parameter). In fact API will reject queries for networks larger than 10 proteins without the specified organism.
When developing your tool use default STRING address (https://string-db.org), but when your code is ready, you should link to a specific STRING version (for example "https://version-12-0.string-db.org"), which will ensure that for the same query you will always get the same API response, even after STRING or API gets updated. To see the current STRING version and its URL prefix click here
STRING understands both GET and POST requests. GET requests, although simpler to use, have a character limit, therefore it is recommended to use POST whenever possible.
When calling our API from your website or tools please identify yourself using the caller_identity parameter.
Mapping identifiersTop ↑
You can call our STRING API with common gene names, various synonyms or even UniProt identifiers and accession numbers. However, STRING may not always understand them which may lead to errors or inconsistencies. Before using other API methods it is always advantageous to map your identifiers to the ones STRING uses. In addition, STRING will resolve its own identifiers faster, therefore your tool/website will see a speed benefit if you use them. For each input protein STRING places the best matching identifier in the first row, so the first line will usually be the correct one.

Call:
https://string-db.org/api/[output-format]/get_string_ids?identifiers=[your_identifiers]&[optional_parameters]
Available output formats:
Format	Description
tsv	tab separated values, with a header line
tsv-no-header	tab separated values, without header line
json	JSON format
xml	XML format
Available parameters:
Parameter	Description
identifiers	required parameter for multiple items, e.g. DRD1_HUMAN%0dDRD2_HUMAN
echo_query	insert column with your input identifier (takes values '0' or '1', default is '0')
species	NCBI/STRING taxon (e.g. 9606 for human, or STRG0AXXXXX see: STRING organisms).
caller_identity	your identifier for us.
Output fields:
Field	Description
queryItem	(OPTIONAL) your input protein
queryIndex	position of the protein in your input (starting from position 0)
stringId	STRING identifier
ncbiTaxonId	NCBI taxon identifier
taxonName	species name
preferredName	common protein name
annotation	protein annotation
Example call (resolving "p53" and "cdk2" in human):
https://string-db.org/api/tsv/get_string_ids?identifiers=p53%0dcdk2&species=9606
Example of python3 code:
#!/usr/bin/env python3

##########################################################
## For a given list of proteins the script resolves them
## (if possible) to the best matching STRING identifier
## and prints out the mapping on screen in the TSV format
##
## Requires requests module:
## type "python -m pip install requests" in command line
## (win) or terminal (mac/linux) to install the module
###########################################################

import requests ## python -m pip install requests

string_api_url = "https://version-12-0.string-db.org/api"
output_format = "tsv-no-header"
method = "get_string_ids"

##
## Set parameters
##

params = {

    "identifiers" : "\r".join(["p53", "BRCA1", "cdk2", "Q99835"]), # your protein list
    "species" : 9606, # NCBI/STRING taxon identifier 
    "echo_query" : 1, # see your input identifiers in the output
    "caller_identity" : "www.awesome_app.org" # your app name

}

##
## Construct URL
##


request_url = "/".join([string_api_url, output_format, method])

##
## Call STRING
##

results = requests.post(request_url, data=params)

##
## Read and parse the results
##

for line in results.text.strip().split("\n"):
    l = line.split("\t")
    input_identifier, string_identifier = l[0], l[2]
    print("Input:", input_identifier, "STRING:", string_identifier, sep="\t")
Getting STRING network imageTop ↑
With our API you can retrieve an image of a STRING network of a neighborhood surrounding one or more proteins or ask STRING to show only the network of interactions between your input proteins. Both the network flavors (confidence and evidence) and network types (functional and physical) are accessible through the API. The API can output the image as a PNG (low and high resolution with alpha-channel) or as an SVG (vector graphics that can be modified through scripts or in an appropriate software).

Call:
https://string-db.org/api/[output-format]/network?identifiers=[your_identifiers]&[optional_parameters]
Available output formats:
Format	Description
image	network PNG image with alpha-channel
highres_image	high resolution network PNG image with alpha-channel
svg	vector graphic format (SVG)
Available parameters:
Data
Parameter	Description
identifiers	required parameter for multiple items, e.g. DRD1_HUMAN%0dDRD2_HUMAN
species	NCBI/STRING taxon (e.g. 9606 for human, or STRG0AXXXXX see: STRING organisms).
add_color_nodes	adds color nodes based on scores to the input proteins
add_white_nodes	adds white nodes based on scores to the input proteins (added after color nodes)
required_score	threshold of significance to include an interaction, a number between 0 and 1000 (default depends on the network)
network_type	network type: functional (default), physical
caller_identity	your identifier for us.
Visual
Parameter	Description
network_flavor	the style of edges in the network: evidence (default), confidence, actions
hide_node_labels	hides all protein names from the picture (0 or 1) (defailt:0)
hide_disconnected_nodes	hides all proteins that are not connected to any other protein in your network (0 or 1) (default:0)
show_query_node_labels	when provided use submitted names as protein labels in the network image (0 or 1) (default:0)
block_structure_pics_in_bubbles	disables structure pictures inside the bubble (0 or 1) (default:0)
flat_node_design	disable 3D bubble design (0 or 1) (default:0)
center_node_labels	center protein names on nodes (0 or 1) (default:0)
custom_label_font_size	change font size of the protein names (from 5 to 50) (default:12)
If you query the API with one protein the "add_white_nodes" parameter is automatically set to 10, so you can see the interaction neighborhood of your query protein. However, similarly to the STRING webpage, whenever you query the API with more than one protein we show only the interactions between your input proteins. You can, of course, always extend the interaction neighborhood by setting "add_color/white_nodes" parameter to the desired value.

Output (yeast's nuclear pore complex):
Nuclear pore complex

Example call (physical interaction neighborhood of nup100 reveals nuclear pore complex):
https://string-db.org/api/image/network?identifiers=nup100&add_color_nodes=10&network_type=physical
Example python3 code:
#!/usr/bin/env python3

################################################################
## For each protein in a list save the PNG image of
## STRING network of its 15 most confident interaction partners.
##
## Requires requests module:
## type "python -m pip install requests" in command line (win)
## or terminal (mac/linux) to install the module
################################################################

import requests ## python -m pip install requests
from time import sleep

string_api_url = "https://version-12-0.string-db.org/api"
output_format = "image"
method = "network"

my_genes = ["YMR055C", "YFR028C",
            "YNL161W", "YOR373W",
            "YFL009W", "YBR202W"]


##
## Construct URL
##


request_url = "/".join([string_api_url, output_format, method])

## For each gene call STRING

for gene in my_genes:

    ##
    ## Set parameters
    ##

    params = {

        "identifiers" : gene, # your protein
        "species" : 4932, # NCBI/STRING taxon identifier 
        "add_white_nodes": 15, # add 15 white nodes to my protein 
        "network_flavor": "confidence", # show confidence links
        "caller_identity" : "www.awesome_app.org" # your app name

    }


    ##
    ## Call STRING
    ##

    response = requests.post(request_url, data=params)

    ##
    ## Save the network to file
    ##

    file_name = "%s_network.png" % gene
    print("Saving interaction network to %s" % file_name)

    with open(file_name, 'wb') as fh:
        fh.write(response.content)

    sleep(1)
Linking to the network on STRING webpageTop ↑
This API allows you to get a link to your network on the STRING webapge. The parameters are the same as retrieving the network through other API methods (as a image or as a text file) and the produced networks will be the same. Generated link is a "stable" one which means it will redirect to the specific STRING version (if not specified with the url prefix, it will link to the current version of STRING).

Call:
https://string-db.org/api/[output-format]/get_link?identifiers=[your_identifiers]&[optional_parameters]
Available output formats:
Format	Description
tsv	tab separated values, with a header line
tsv-no-header	tab separated values, without header line
json	JSON format
xml	XML format
Available parameters:
Parameter	Description
identifiers	required parameter for multiple items, e.g. DRD1_HUMAN%0dDRD2_HUMAN
species	NCBI/STRING taxon (e.g. 9606 for human, or STRG0AXXXXX see: STRING organisms).
add_color_nodes	adds color nodes based on scores to the input proteins
add_white_nodes	adds white nodes based on scores to the input proteins (added after color nodes)
required_score	threshold of significance to include an interaction, a number between 0 and 1000 (default depends on the network)
network_flavor	the style of edges in the network: evidence (default), confidence, actions
network_type	network type: functional (default), physical
hide_node_labels	hides all protein names from the picture (0 or 1) (defailt:0)
hide_disconnected_nodes	hides all proteins that are not connected to any other protein in your network (0 or 1) (default:0)
show_query_node_labels	when provided use submitted names as protein labels in the network image (0 or 1) (default:0)
block_structure_pics_in_bubbles	disables structure pictures inside the bubble (0 or 1) (default:0)
caller_identity	your identifier for us.
If you query the API with one protein the "add_color_nodes" parameter is automatically set to 10. Whenever you query the API with more than one protein we show only the interactions between your input proteins. You can, of course, always extend the interaction neighborhood by setting "add_color/white_nodes" parameter to the desired value.

Output fields:
Field	Description
url	stable link to the network
Example call (Link to Drosophila's smoothened protein interaction neighborhood):
https://string-db.org/api/tsv/get_link?identifiers=SMO&species=7227
Linking to the search results pageTop ↑
This section details how you can embed links on your website to directly access STRING's search results page or specific protein networks. This functionality is useful for setting up a search feature that lets users query STRING using the proteins listed on your site, without the need for converting them into STRING's specific identifiers. The link will direct the user to the search results, identical to the way the user would search for protein in the STRING input page. Specifying the species is optional; if omitted, users are first directed to a species disambiguation page. Providing a species bypasses this step, leading straight to protein disambiguation. Using STRING identifiers (like 511145.b1260 or 9606.ENSP00000269305) will skip disambiguation entirely, directing users directly to the respective network. For single protein searches, STRING automatically adds the 10 most confident interactions to the network, a default setting that can be altered. For multiple protein queries, the option to retain the original query names is available, which is particularly useful if your application operates in a different naming convention.

Link:
https://string-db.org/cgi/network?identifiers=[your_identifiers]&[optional_parameters]
Available parameters:
Parameter	Description
identifiers	required parameter for multiple items, e.g. DRD1_HUMAN%0dDRD2_HUMAN
species	NCBI/STRING taxon (e.g. 9606 for human, or STRG0AXXXXX see: STRING organisms).
add_color_nodes	adds color nodes based on scores to the input proteins
add_white_nodes	adds white nodes based on scores to the input proteins (added after color nodes)
required_score	threshold of significance to include an interaction, a number between 0 and 1000 (default depends on the network)
network_flavor	the style of edges in the network: evidence (default), confidence, actions
network_type	network type: functional (default), physical
hide_node_labels	hides all protein names from the picture (0 or 1) (defailt:0)
hide_disconnected_nodes	hides all proteins that are not connected to any other protein in your network (0 or 1) (default:0)
show_query_node_labels	when provided use submitted names as protein labels in the network image (0 or 1) (default:0)
block_structure_pics_in_bubbles	disables structure pictures inside the bubble (0 or 1) (default:0)
caller_identity	your identifier for us.
If you search with one protein the "add_color_nodes" parameter is automatically set to 10. Whenever you query the API with more than one protein we show only the interactions between your input proteins. You can, of course, always extend the interaction neighborhood by setting "add_color/white_nodes" parameter to the desired value.

Example link (P53/MDM2/ATM human network retaining the uniprot namespace)
https://string-db.org/cgi/network?identifiers=P53_HUMAN%0dMDM2_HUMAN%0dATM_HUMAN&species=9606&show_query_node_labels=1
Embedding the interactive networkTop ↑
Using provided simple HTML and JavaScript code you can embed the interactive STRING network in your website or webApp. The advantages of the interactive network are several: 1) The user can move the nodes around to explore the network's structure 2) each node can be clicked and a pop-up will appear above the network providing information about the protein's structure, its function and sequence 3) the network contains a link-out to STRING that lets the user jump directly to STRING website and explore interactions in even more details. The behaviour of the API is similar to the Getting the network image API, that is, it lets you retrieve either 1) the image of the interaction neighborhood of one or more proteins and 2) the image of the interaction network only between the specified set of proteins. The two APIs also shares the exact same set of parametes.

Code:
First your website has to load two elements to make it work. IMPORTANT: Do not load these elements in the iFrame - if you do the pop-ups will be confiened only to the iFrame instead of overlaying your website.

The first element is a small STRING's javascript library that allows for moveable bubbles and pop-ups.

<script type="text/javascript" src="https://string-db.org/javascript/combined_embedded_network_v2.0.4.js"></script>
The second is an HTML DIV element. You insert in the place where you want the network to displayed. You can assign any class to this element or style it however you want, just do not change its identifier.

<div id="stringEmbedded"></div>
And finally this API call in Javascript:

getSTRING('https://string-db.org', {[dictionary of parameters]})">
Available parameters:
Parameter	Description
identifiers	required parameter - array of protein names e.g. ['TP53', 'CDK2']
species	NCBI/STRING taxon (e.g. 9606 for human, or STRG0AXXXXX see: STRING organisms).
add_color_nodes	adds color nodes based on scores to the input proteins
add_white_nodes	adds white nodes based on scores to the input proteins (added after color nodes)
required_score	threshold of significance to include an interaction, a number between 0 and 1000 (default depends on the network)
network_flavor	the style of edges in the network: evidence (default), confidence, actions
network_type	network type: functional (default), physical
hide_node_labels	hides all protein names from the picture (0 or 1) (defailt:0)
hide_disconnected_nodes	hides all proteins that are not connected to any other protein in your network (0 or 1) (default:0)
show_query_node_labels	when provided use submitted names as protein labels in the network image (0 or 1) (default:0)
block_structure_pics_in_bubbles	disables structure pictures inside the bubble (0 or 1) (default:0)
caller_identity	your identifier for us.
Example JavaScript call (TP53 interaction neighborhood):
getSTRING('https://string-db.org', {'species':'9606', 'identifiers':['TP53'], 'network_flavor':'confidence'})">
Example website code (to test it copy paste it into an empty file with .html extenstion and open it in your browser):
<!DOCTYPE html>
<html>
  <head>

      <!-- Embed the STRING's javascript -->

      <script type="text/javascript" src="https://string-db.org/javascript/combined_embedded_network_v2.0.4.js"></script>

      <style>

           /* some styling */

           body {
               font-family: Arial;
               color: #122e4d;
               background: #cedded;
           }

           input {
               border: 4px solid #122e4d; 
               width: 40%;
               height: 50px;
               border-radius: 10px;  
               font-size: 20px;
           }

           button {
               font-size:20px;
               border-radius: 10px;  
               border: 1px solid #122e4d; 
           }

      </style>
      <script>

          function send_request_to_string() {

              var inputField = document.getElementById('inputarea');

              var text = inputField.value;

              if (!text) {text = inputField.placeholder}; // placeholder

              var proteins = text.split(' ');

              /* the actual API query */

              getSTRING('https://string-db.org', {
                          'species':'9606',
                          'identifiers':proteins,
                          'network_flavor':'confidence', 
                          'caller_identity': 'www.awesome_app.org'
              })

          }

      </script>
  </head>

  <!-- HTML CODE -->

  <body onload='javascript:send_request_to_string()'>
      <center>
          <h1>YOUR WEBSITE</h1>
          <h3>Query me: (one human protein or multiple space seperated proteins)</h3>
             <input type="text" id='inputarea' placeholder='GLI3'><br/></br/>
             <button onclick='javascript:send_request_to_string();' type="button">Let's go!</button>
             <h3>Network:</h3>
             <div id="stringEmbedded"></div>
      </center>
  </body>
</html>
Getting the STRING network interactionsTop ↑
The network API method also allows you to retrieve your STRING interaction network for one or multiple proteins in various text formats. It will tell you the combined score and all the channel specific scores for the set of proteins. You can also extend the network neighborhood by setting "add_nodes", which will add, to your network, new interaction partners in order of their confidence.

Call:
https://string-db.org/api/[output-format]/network?identifiers=[your_identifiers]&[optional_parameters]
Available output formats:
Format	Description
tsv	tab separated values, with a header line
tsv-no-header	tab separated values, without header line
json	JSON format
xml	XML format
psi-mi	PSI-MI XML format
psi-mi-tab	PSI-MITAB format
Available parameters:
Parameter	Description
identifiers	required parameter for multiple items, e.g. DRD1_HUMAN%0dDRD2_HUMAN
species	NCBI/STRING taxon (e.g. 9606 for human, or STRG0AXXXXX see: STRING organisms).
required_score	threshold of significance to include a interaction, a number between 0 and 1000 (default depends on the network)
network_type	network type: functional (default), physical
add_nodes	adds a number of proteins with to the network based on their confidence score
show_query_node_labels	when available use submitted names in the preferredName column when (0 or 1) (default:0)
caller_identity	your identifier for us.
If you query the API with one protein the "add_nodes" parameter is automatically set to 10, so you can can get the interaction neighborhood of your query protein. However, similarly to the STRING webpage, whenever you query the API with more than one protein the method will output only the interactions between your input proteins. You can, of course, always extend the interaction neighborhood by setting "add_nodes" parameter to the desired value.

Output fields (TSV and JSON formats):
Field	Description
stringId_A	STRING identifier (protein A)
stringId_B	STRING identifier (protein B)
preferredName_A	common protein name (protein A)
preferredName_B	common protein name (protein B)
ncbiTaxonId	NCBI taxon identifier
score	combined score
nscore	gene neighborhood score
fscore	gene fusion score
pscore	phylogenetic profile score
ascore	coexpression score
escore	experimental score
dscore	database score
tscore	textmining score
To see how the combined score is computed from the partial scores see FAQ

Example call (retrieve all interactions between TP53 EGFR and CDK2):
https://string-db.org/api/tsv/network?identifiers=TP53%0dEGFR%0dCDK2&required_score=400
Example python3 code:
#!/usr/bin/env python3

##################################################################
## For the given list of proteins print out only the interactions
## between these protein which have medium or higher confidence
## experimental score
##
## Requires requests module:
## type "python -m pip install requests" in command line (win)
## or terminal (mac/linux) to install the module
##################################################################

import requests ## python -m pip install requests


string_api_url = "https://version-12-0.string-db.org/api"
output_format = "tsv-no-header"
method = "network"

##
## Construct URL
##

request_url = "/".join([string_api_url, output_format, method])

##
## Set parameters
##

my_genes = ["CDC42","CDK1","KIF23","PLK1",
            "RAC2","RACGAP1","RHOA","RHOB"]

params = {

    "identifiers" : "%0d".join(my_genes), # your protein
    "species" : 9606, # NCBI/STRING taxon identifier 
    "caller_identity" : "www.awesome_app.org" # your app name

}

##
## Call STRING
##

response = requests.post(request_url, data=params)

for line in response.text.strip().split("\n"):

    l = line.strip().split("\t")
    p1, p2 = l[2], l[3]

    ## filter the interaction according to experimental score
    experimental_score = float(l[10])
    if experimental_score > 0.4:
        ## print 
        print("\t".join([p1, p2, "experimentally confirmed (prob. %.3f)" % experimental_score]))
Getting all the STRING interaction partners of the protein setTop ↑
Diffrently from the network API method, which retrieves only the interactions between the set of input proteins and between their closest interaction neighborhood (if add_nodes parameters is specified), interaction_partners API method provides the interactions between your set of proteins and all the other STRING proteins. The output is available in various text based formats. As STRING network usually has a lot of low scoring interactions, you may want to limit the number of retrieved interaction per protein using "limit" parameter (of course the high scoring interactions will come first).

Call:
https://string-db.org/api/[output-format]/interaction_partners?identifiers=[your_identifiers]&[optional_parameters]
Available output formats:
Format	Description
tsv	tab separated values, with a header line
tsv-no-header	tab separated values, without header line
json	JSON format
xml	XML format
psi-mi	PSI-MI XML format
psi-mi-tab	PSI-MITAB format
Available parameters:
Parameter	Description
identifiers	required parameter for multiple items, e.g. DRD1_HUMAN%0dDRD2_HUMAN
species	NCBI/STRING taxon (e.g. 9606 for human, or STRG0AXXXXX see: STRING organisms).
limit	limits the number of interaction partners retrieved per protein (most confident interactions come first)
required_score	threshold of significance to include a interaction, a number between 0 and 1000 (default depends on the network)
network_type	network type: functional (default), physical
caller_identity	your identifier for us.
Output fields (TSV and JSON formats):
Field	Description
stringId_A	STRING identifier (protein A)
stringId_B	STRING identifier (protein B)
preferredName_A	common protein name (protein A)
preferredName_B	common protein name (protein B)
ncbiTaxonId	NCBI taxon identifier
score	combined score
nscore	gene neighborhood score
fscore	gene fusion score
pscore	phylogenetic profile score
ascore	coexpression score
escore	experimental score
dscore	database score
tscore	textmining score
To see how the combined score is computed from the partial scores see FAQ

Example call (retrieve best 10 STRING interactions for TP53 and CDK2):
https://string-db.org/api/tsv/interaction_partners?identifiers=TP53%0dCDK2&limit=10
Example python3 code:
#!/usr/bin/env python3

################################################################
## For each protein in the given list print the names of
## their 5 best interaction partners.
##
## Requires requests module:
## type "python -m pip install requests" in command line (win)
## or terminal (mac/linux) to install the module
################################################################


import requests ## python -m pip install requests

string_api_url = "https://version-12-0.string-db.org/api"
output_format = "tsv-no-header"
method = "interaction_partners"

my_genes = ["9606.ENSP00000000233", "9606.ENSP00000000412",
            "9606.ENSP00000000442", "9606.ENSP00000001008"]

##
## Construct the request
##

request_url = "/".join([string_api_url, output_format, method])

##
## Set parameters
##

params = {

    "identifiers" : "%0d".join(my_genes), # your protein
    "species" : 9606, # NCBI/STRING taxon identifier 
    "limit" : 5,
    "caller_identity" : "www.awesome_app.org" # your app name

}


##
## Call STRING
##

response = requests.post(request_url, data=params)

##
## Read and parse the results
##

for line in response.text.strip().split("\n"):

    l = line.strip().split("\t")
    query_ensp = l[0]
    query_name = l[2]
    partner_ensp = l[1]
    partner_name = l[3]
    combined_score = l[5]

    ## print

    print("\t".join([query_ensp, query_name, partner_name, combined_score]))
Retrieving similarity scores of the protein setTop ↑
STRING internally uses the Smith–Waterman bit scores as a proxy for protein homology. The original scores are computed by SIMILARITY MATRIX OF PROTEINS (SIMAP) project. Using this API you can retrieve these scores between the proteins in a selected species. They are symmetric, therefore to make the transfer a bit faster we will send only half of the similarity matrix (A->B, but not symmetric B->A) and the self-hits. The bit score cut-off below which we do not store or report homology is 50.

Call:
https://string-db.org/api/[output-format]/homology?identifiers=[your_identifiers]
Available output formats:
Format	Description
tsv	tab separated values, with a header line
tsv-no-header	tab separated values, without header line
json	JSON format
xml	XML format
Available parameters:
Parameter	Description
identifiers	required parameter for multiple items, e.g. DRD1_HUMAN%0dDRD2_HUMAN
species	NCBI/STRING taxon (e.g. 9606 for human, or STRG0AXXXXX see: STRING organisms).
caller_identity	your identifier for us.
Output fields (TSV and JSON formats):
Field	Description
ncbiTaxonId_A	NCBI taxon identifier (protein A)
stringId_A	STRING identifier (protein A)
ncbiTaxonId_B	NCBI taxon identifier (protein B)
stringId_B	STRING identifier (protein B)
bitscore	Smith-Waterman alignment bit score
Example call (retrieve homology scores between CDK1 and CDK2)
https://string-db.org/api/tsv/homology?identifiers=CDK1%0dCDK2
Retrieving best similarity hits between speciesTop ↑
STRING internally uses the Smith–Waterman bit scores as a proxy for protein homology. The original scores are computed by SIMILARITY MATRIX OF PROTEINS (SIMAP) project. Using this API you can retrieve these similarity scores between your input proteins and proteins in all of the STRING's organisms. Only the best hit per organism for each protein will be retrieved.

There are many organisms in STRING, so expect thousands hits for each protein, however you can filter the results to the list of organisms of interest by using 'species_b' parameter.

Call:
https://string-db.org/api/[output-format]/homology_best?identifiers=[your_identifiers]
Available output formats:
Format	Description
tsv	tab separated values, with a header line
tsv-no-header	tab separated values, without header line
json	JSON format
xml	XML format
Available parameters:
Parameter	Description
identifiers	required parameter for multiple items, e.g. DRD1_HUMAN%0dDRD2_HUMAN
species	NCBI/STRING taxon (e.g. 9606 for human, or STRG0AXXXXX see: STRING organisms).
species_b	a list of NCBI taxon identifiers seperated by "%0d" (e.g. human, fly and yeast would be "9606%0d7227%0d4932" see: STRING organisms).
caller_identity	your identifier for us.
Output fields (TSV and JSON formats):
Field	Description
ncbiTaxonId_A	NCBI taxon identifier (protein A)
stringId_A	STRING identifier (protein A)
ncbiTaxonId_B	NCBI taxon identifier (protein B)
stringId_B	STRING identifier (protein B)
bitscore	Smith-Waterman alignment bit score
Example call (retrieve best homology score between human CDK1 and its closest mouse homolog)
https://string-db.org/api/tsv/homology_best?identifiers=CDK1&species_b=10090
Getting functional enrichmentTop ↑
STRING maps several databases onto its proteins, this includes: Gene Ontology, KEGG pathways, UniProt Keywords, PubMed publications, Pfam domains, InterPro domains, and SMART domains.The STRING enrichment API method allows you to retrieve functional enrichment for any set of input proteins. It will tell you which of your input proteins have an enriched term and the term's description. The API provides the raw p-values, as well as, False Discovery Rate (B-H corrected p-values). The detailed description of the enrichment algorithm can be found here

NOTE: As with other STRING APIs, we automatically expand the network by 10 proteins when a query includes only one protein. Keep in mind that this network expansion will likely reduce the FDR more than expected by chance and does not indicate an enrichment of the original single-protein set but rather of its immediate interaction neighborhood. When querying with a set of two or more proteins, no additional proteins are added to the input, and the FDR accurately reflects the probability of observing the enrichment by random chance.

Call:
https://string-db.org/api/[output_format]/enrichment?identifiers=[your_identifiers]&[optional_parameters]
Available output formats:
Format	Description
tsv	tab separated values, with a header line
tsv-no-header	tab separated values, without header line
json	JSON format
xml	XML format
Available parameters:
Parameter	Description
identifiers	required parameter for multiple items, e.g. DRD1_HUMAN%0dDRD2_HUMAN
background_string_identifiers	using this parameter you can specify the background proteome of your experiment. Only STRING identifiers will be recognised (each must be seperated by "%0d") e.g. '7227.FBpp0077451%0d7227.FBpp0074373'. You can map STRING identifiers using mapping identifiers method.
species	NCBI/STRING taxon (e.g. 9606 for human, or STRG0AXXXXX see: STRING organisms).
caller_identity	your identifier for us.
Output fields:
Field	Description
category	term category (e.g. GO Process, KEGG pathways)
term	enriched term (GO term, domain or pathway)
number_of_genes	number of genes in your input list with the term assigned
number_of_genes_in_background	total number of genes in the background proteome with the term assigned
ncbiTaxonId	NCBI taxon identifier
inputGenes	gene names from your input
preferredNames	common protein names (in the same order as your input Genes)
p_value	raw p-value
fdr	False Discovery Rate
description	description of the enriched term
STRING shows only the terms with the raw p-value below 0.1

Example call (E. coli Tryptophan biosynthetic process genes):
https://string-db.org/api/tsv/enrichment?identifiers=trpA%0dtrpB%0dtrpC%0dtrpE%0dtrpGD
Example python3 code:
#!/usr/bin/env python3

##############################################################
## The following script retrieves and prints out
## significantly enriched (FDR < 1%) GO Processes
## for the given set of proteins. 
##
## Requires requests module:
## type "python -m pip install requests" in command line (win)
## or terminal (mac/linux) to install the module
##############################################################

import requests ## python -m pip install requests 
import json

string_api_url = "https://version-12-0.string-db.org/api"
output_format = "json"
method = "enrichment"


##
## Construct the request
##

request_url = "/".join([string_api_url, output_format, method])

##
## Set parameters
##

my_genes = ['7227.FBpp0074373', '7227.FBpp0077451', '7227.FBpp0077788',
            '7227.FBpp0078993', '7227.FBpp0079060', '7227.FBpp0079448']

params = {

    "identifiers" : "%0d".join(my_genes), # your protein
    "species" : 7227, # NCBI/STRING taxon identifier 
    "caller_identity" : "www.awesome_app.org" # your app name

}

##
## Call STRING
##

response = requests.post(request_url, data=params)

##
## Read and parse the results
##

data = json.loads(response.text)

for row in data:

    term = row["term"]
    preferred_names = ",".join(row["preferredNames"])
    fdr = float(row["fdr"])
    description = row["description"]
    category = row["category"]

    if category == "Process" and fdr < 0.01:

        ## print significant GO Process annotations

        print("\t".join([term, preferred_names, str(fdr), description]))
Retrieving functional annotationTop ↑
STRING maps several databases onto its proteins, this includes: Gene Ontology, KEGG pathways, UniProt Keywords, PubMed publications, Pfam domains, InterPro domains, and SMART domains. You can retrieve all these annotations (and not only enriched subset) for your proteins via this API. Due to the potential large size of the PubMed (Reference Publications) assignments, they won't be sent by default, but you can turn them back on by specifying the 'allow_pubmed=1' parameter.

Please note: KEGG annotations are not available due to KEGG licence restrictions.

Call:
https://string-db.org/api/[output_format]/functional_annotation?identifiers=[your_identifiers]&[optional_parameters]
Available output formats:
Format	Description
tsv	tab separated values, with a header line
tsv-no-header	tab separated values, without header line
json	JSON format
xml	XML format
Available parameters:
Parameter	Description
identifiers	required parameter for multiple items, e.g. DRD1_HUMAN%0dDRD2_HUMAN
species	NCBI/STRING taxon (e.g. 9606 for human, or STRG0AXXXXX see: STRING organisms).
allow_pubmed	'1' to print also the PubMed annotations in addition to other categories, default is '0'
only_pubmed	'1' to print only PubMed annotations, default is '0'
caller_identity	your identifier for us.
Output fields:
Field	Description
category	term category (e.g. GO Process, KEGG pathways)
term	enriched term (GO term, domain or pathway)
number_of_genes	number of genes in your input list with the term assigned
ratio_in_set	ratio of the proteins in your input list with the term assigned
ncbiTaxonId	NCBI taxon identifier
inputGenes	gene names from your input
preferredNames	common protein names (in the same order as your input Genes)
description	description of the enriched term
Example call (Human CDK1 functional annotation):
https://string-db.org/api/tsv/functional_annotation?identifiers=cdk1
Retrieving enrichment figureTop ↑
This API enables the visualization of enrichment analysis, providing a way to explore results across three key dimensions:

Enrichment signal (X-axis)
False Discovery Rate (FDR) represented by the dot color
Protein count in the network indicated by the dot size
The Y-axis lists enriched terms, ranked by a selected variable (signal, strength, FDR, or gene count). Terms can be grouped using the Jaccard index ('group_by_similarity' parameter), clustering similar terms to highlight relationships between them.

This API functions similarly to the enrichment API but visualizes the results only for a single category (default: Gene Ontology Biological Process).

NOTE: As with other STRING APIs, we automatically expand the network by 10 proteins when a query includes only one protein. Keep in mind that this network expansion will likely reduce the FDR more than expected by chance and does not indicate an enrichment of the original single-protein set but rather of its immediate interaction neighborhood. When querying with a set of two or more proteins, no additional proteins are added to the input, and the FDR accurately reflects the probability of observing the enrichment by random chance.

Call:
https://string-db.org/api/[output_format]/enrichmentfigure?identifiers=[your_identifiers]&species=[your_species]&category=[your_category]
Available output formats:
Format	Description
image	network PNG image with alpha-channel
highres_image	high resolution network PNG image with alpha-channel
svg	vector graphic format (SVG)
Available parameters:
Parameter	Description
identifiers	required parameter for multiple items, e.g. DRD1_HUMAN%0dDRD2_HUMAN
species	NCBI/STRING taxon (e.g. 9606 for human, or STRG0AXXXXX see: STRING organisms).
category	term category (e.g., KEGG, WikiPathways, etc. See the table below for all category keys. Default is Process)
group_by_similarity	threshold for visually grouping related terms on the plot, ranging from 0.1 to 1, in steps of 0.1 (e.g. 0.8), with no grouping applied by default.
color_palette	color palette to represent FDR values (mint_blue, lime_emerald, green_blue, peach_purple, straw_navy, yellow_pink, default is mint_blue).
number_of_term_shown	maximum number of terms displayed on the plot (default is 10).
x_axis	specifies the order of the terms and the variable on the X-axis (signal, strength, FDR, gene_count, default is signal).
STRING provides enrichment visualizations for the following categories. The category ID is used in API calls.

Category ID	Description
Process	Biological Process (Gene Ontology)
Function	Molecular Function (Gene Ontology)
Component	Cellular Component (Gene Ontology)
Keyword	Annotated Keywords (UniProt)
KEGG	KEGG Pathways
RCTM	Reactome Pathways
HPO	Human Phenotype (Monarch)
MPO	The Mammalian Phenotype Ontology (Monarch)
DPO	Drosophila Phenotype (Monarch)
WPO	C. elegans Phenotype Ontology (Monarch)
ZPO	Zebrafish Phenotype Ontology (Monarch)
FYPO	Fission Yeast Phenotype Ontology (Monarch)
Pfam	Protein Domains (Pfam)
SMART	Protein Domains (SMART)
InterPro	Protein Domains and Features (InterPro)
PMID	Reference Publications (PubMed)
NetworkNeighborAL	Local Network Cluster (STRING)
COMPARTMENTS	Subcellular Localization (COMPARTMENTS)
TISSUES	Tissue Expression (TISSUES)
DISEASES	Disease-gene Associations (DISEASES)
WikiPathways	WikiPathways
Example output (Biological Process (GO) enrichment for the melanoma protein network):
Melanoma enrichment figure

Example call:
https://string-db.org/api/image/enrichmentfigure?identifiers=ARRB1%0dARRB2%0dEVC%0dPTCH1%0dSHH%0dSMO&species=9606&category=Function&group_by_similarity=0.5&color_palette=yellow_pink&x_axis=FDR
Example python3 code:
#!/usr/bin/env python3

##############################################################
## The following script retrieves the enrichment figure
## for as a png (with transparency) for a specific 
## category (Gene Ontology Biological Process)
##
##
## Requires requests module:
## type "python -m pip install requests" in command line (win)
## or terminal (mac/linux) to install the module
##############################################################

import requests ## python -m pip install requests

string_api_url = "https://version-12-0.string-db.org/api"
output_format = "image"
method = "enrichmentfigure"

image_filename = 'enrichment_figure.png'

##
## Construct the request
##

request_url = "/".join([string_api_url, output_format, method])

##
## Set parameters
##

my_genes = ['7227.FBpp0074373', '7227.FBpp0077451', '7227.FBpp0077788',
            '7227.FBpp0078993', '7227.FBpp0079060', '7227.FBpp0079448']

params = {

    "identifiers" : "%0d".join(my_genes), # your protein list
    "species" : 7227, # NCBI/STRING taxon identifier 
    "caller_identity" : "www.awesome_app.org",
    "group_by_similarity" : 0.8,
    "x_axis" : 'FDR',
    "category" : "Process",
    "color_palette" : "yellow_pink",

}

##
## Call STRING
##

response = requests.post(request_url, data=params)

if response.status_code == 200:
    with open(image_filename, "wb") as f:
        f.write(response.content)
    print(f"Image saved as '{image_filename}'")
else:
    print(f"Failed to retrieve image. Status code: {response.status_code}")
Getting protein-protein interaction enrichmentTop ↑
Even in the absence of annotated proteins (e.g. in novel genomes) STRING can tell you if your subset of proteins is functionally related, that is, if it is enriched in interactions in comparison to the background proteome-wide interaction distribution. The detailed description of the PPI enrichment method can be found here

Call:
https://string-db.org/api/[output_format]/ppi_enrichment?identifiers=[your_identifiers]&[optional_parameters]
Available output formats:
Format	Description
tsv	tab separated values, with a header line
tsv-no-header	tab separated values, without header line
json	JSON format
xml	XML format
Available parameters:
Parameter	Description
identifiers	required parameter for multiple items, e.g. DRD1_HUMAN%0dDRD2_HUMAN
species	NCBI/STRING taxon (e.g. 9606 for human, or STRG0AXXXXX see: STRING organisms).
required_score	threshold of significance to include a interaction, a number between 0 and 1000 (default depends on the network)
background_string_identifiers	using this parameter you can specify the background proteome of your experiment. Only STRING identifiers will be recognised (each must be seperated by "%0d") e.g. '7227.FBpp0077451%0d7227.FBpp0074373'. You can map STRING identifiers using mapping identifiers method.
caller_identity	your identifier for us.
Output fields:
Field	Description
number_of_nodes	number of proteins in your network
number_of_edges	number of edges in your network
average_node_degree	mean degree of the node in your network
local_clustering_coefficient	average local clustering coefficient
expected_number_of_edges	expected number of edges based on the nodes degrees
p_value	significance of your network having more interactions than expected
Example call (the network neighborhood of Epidermal growth factor receptor):
https://string-db.org/api/tsv/ppi_enrichment?identifiers=trpA%0dtrpB%0dtrpC%0dtrpE%0dtrpGD
Example python3 code:
#!/usr/bin/env python

##############################################################
## The script prints out the p-value of STRING protein-protein
## interaction enrichment method for the given set of proteins 
##
## Requires requests module:
## type "python -m pip install requests" in command line (win)
## or terminal (mac/linux) to install the module
##############################################################

import requests ## python -m pip install requests

string_api_url = "https://version-12-0.string-db.org/api"
output_format = "tsv-no-header"
method = "ppi_enrichment"

##
## Construct the request
##

request_url = "/".join([string_api_url, output_format, method])

##
## Set parameters
##

my_genes = ['7227.FBpp0074373', '7227.FBpp0077451', '7227.FBpp0077788',
            '7227.FBpp0078993', '7227.FBpp0079060', '7227.FBpp0079448']

params = {

    "identifiers" : "%0d".join(my_genes), # your proteins
    "species" : 7227, # NCBI/STRING taxon identifier 
    "caller_identity" : "www.awesome_app.org" # your app name

}

##
## Call STRING
##

response = requests.post(request_url, data=params)

##
## Parse and print the respons Parse and print the responsee
##

for line in response.text.strip().split("\n"):
    pvalue = line.split("\t")[5]
    print("P-value:", pvalue)
Getting current STRING versionTop ↑
STRING is updated, on average, every two years. Maybe you would like to download the latest version of STRING's genomes, or simply you would like to be informed if the new version is released. For this you can use the version API, which tell you the latest version of STRING and its stable address. The 'stable address' is an address that does not change beteween version, so if you use the stable API address it will always produce the results from that particular version.

Call:
https://string-db.org/api/[output_format]/version
Available output formats:
Format	Description
tsv	tab separated values, with a header line
tsv-no-header	tab separated values, without header line
json	JSON format
xml	XML format
Available parameters:
None

Output fields:
Field	Description
string_version	current string version
string_stable_address	STRING stable url
Example call:
https://string-db.org/api/json/version
Additional information about the APITop ↑
If you need to do a large-scale analysis, please download the full data set. Otherwise you may end up flooding the STRING server with API requests. In particular, try to avoid running scripts in parallel :)

Please contact us if you have any questions regarding the API.

Values/ranks enrichment API
General overviewTop ↑
The Values/Ranks Enrichment API provides a way to analyze protein datasets using the protein/values ranks enrichment method in STRING. This tool is designed to detect signals based on the provided values, identifying whether specific pathways are significantly enriched at the top, bottom, or both ends of your values distribution.

This method requires the complete set of proteins from your experiment (no cut-offs or subsets) along with associated values such as p-values, differential expression, or t-statistics, offering an analysis similar to Gene Set Enrichment Analysis (GSEA). It achieves high sensitivity through a combination of the KS and AFC tests, assessing your experiment against a comprehensive set of functional categories, complete with visualization and protein mapping functionalities.

Please note that the method is computationally intensive and does not produce immediate results. You will need to obtain an API key, which will enable you to monitor all your submitted analysis. The key is free of charge and remains completely anonymous. Below you'll find the step by step guide how to run the enrichment using the API.

Obtain your API KeyTop ↑
To access the values/ranks enrichment API, you must first request a user API key. This key is required to identify and manage your analysis tasks (jobs) and serves as your anonymous user identifier.

Once requested, your key will be activated within 30 minutes. The key does not expire and allows for up to 1000 queued analysis jobs at the same time. If you need to process more than 1000 jobs, please submit them in consecutive batches of 1000. You will need to wait for the first batch to complete before submitting the next one. There is no lifetime limit on the total number of processed jobs.

Please save your key securely. The key is completely anonymous, and if you lose it, we will not be able to identify you or recover it. Please avoid requesting multiple keys to ensure fair usage of the resources.

Call:
https://version-12-0.string-db.org/api/json/get_api_key
Output example
[{"api_key": "[your_key]", "note": "This key will be activated within 30 minutes."}]
Prepare the data for the analysisTop ↑
Your input data must be a tab-separated text/file with two columns:

The first column should contain protein identifiers / gene symbols
The second column should contain the associated value (e.g., p-value, fold-change, rank, or t-statistics).
Make sure the columns are separated by a tab and that the file does not include any headers.

You can download an example dataset here.

To ensure your data is in the correct format you can submit one dataset manually on the website. If no intervention (other than clicking continue) is required to obtain the analysis results, the automated analysis will also proceed without issues.

Important Note: You can use any protein identifier or gene symbol recognized by STRING. However, for faster processing, we strongly recommend mapping your identifiers to STRING IDs using the get_string_ids method before submission. When you submit data using STRING IDs (e.g. 9606.ENSP00000249373), STRING will skip the mapping step significantly reducing processing time.

Submit a new jobTop ↑
After obtaining an API key from the get_api_key endpoint, and preparing your data you can now submit your data for the values/ranks enrichment analysis. For this you use the valuesranks_enrichment_submit method. This method will queue and execute the analysis (job) on our server, returning a response indicating whether the submission was successful or if there was an error.

Upon submission, the API will confirm whether the submission was successful and return a job_id for tracking. You should store the job_id for the subsequent retrieval of the results. Once submitted, the job is queued on our servers and will be processed as computational resources become available. Processing times depend on system load and dataset complexity; larger datasets or those with more robust functional signals may take longer to analyze.

You can track the status of your job using the valuesranks_enrichment_status endpoint (see below), which provides updates on the job's progress. Once the job is complete, the results, including downloadable outputs and figures, can be retrieved through the same status endpoint (see below).

Available parameters:
Parameter	Description
api_key	Required. API key used to authenticate the user. This is generated once using the get_api_key method.
identifiers	Required. A string containing tab-separated (protein, value) pairs, where the first part is the protein identifier and the second part is the associated value (e.g., rank, p-value).
species	Required. NCBI/STRING taxon (e.g. 9606 for human, or STRG0AXXXXX see: STRING organisms).
ge_fdr	The False Discovery Rate (FDR) stringency level for the analysis (default 0.01).
caller_identity	your identifier for us.
Example python3 code:
##############################################################
## The following script submits a job to the protein with
## values/ranks enrichment analaysis.
##
## Requires requests module:
## type "python -m pip install requests" in command line (win)
## or terminal (mac/linux) to install the module
##############################################################

import requests ## python -m pip install requests
import json

string_api_url = "https://version-12-0.string-db.org/api"
output_format = "json"
method = "valuesranks_enrichment_submit"


##
## Construct the request
##

request_url = "/".join([string_api_url, output_format, method])

##
## Get the input data.
##
## An example dataset can be downloaded here: 
## https://stringdb-downloads.org/download/FC_melanoma_vs_normal.tsv
##

input_file_path = "./FC_melanoma_vs_normal.tsv" ## example dataset

##
## Read the input data as string
##

identifiers = open(input_file_path).read()

##
## Set parameters
##

params = {
    "species": 9606,  # NCBI/STRING species identifier (e.g., 9606 for human)
    "caller_identity": "www.awesome_app.org",
    "identifiers": identifiers,
    "api_key": "[your_api_key]",
    "ge_fdr": 0.05,
    "ge_enrichment_rank_direction": -1
}

##
## Call STRING
##

response = requests.post(request_url, data=params)

##
## Read and parse the result
##

data = json.loads(response.text)[0]



if 'status' in data and data['status'] == 'error':

    print("Status:", data['status'])
    print("Message:", data['message'])

else:

    job_id = data["job_id"]
    print(f"Job submitted successfully. Job ID: {job_id}")
Check job status and retrieve the resultsTop ↑
After submitting your job, you can track its progress to determine which stage of the calculation process it is currently in. This allows you to stay informed about the job's status, more specifically if it's queued, running or completed. When the job finishes successfully, this call will provide links to the result dataset including:

Enrichment Results Table: The tab-seperated file with enrichmed terms, their proteins, p-values etc.
Website Link: Link to STRING website when you can manually explore the results of the analysis.
Enrichment Figure: enrichment visualization figure of your analysis (see also enrichmentfigure method).
In order to check the status of a particular analysis you need to provide the job_id given to you when you have submitted the dataset for the analysis using the submit method. If you do not provide the job_id parameter the method will list all the current and past analysis jobs associated with your api_key, from where you can find your job.

Call:
https://version-12-0.string-db.org/api/json/valuesranks_enrichment_status?api_key=[your_api_key]&job_id=[your_job_id]
Example output (results of DE analysis of melanoma vs. normal tissues)
[
    {
        "job_id": "b0TyfmJPSkIs",
        "creation_time": "2025-01-17 09:47:28",
        "string_version": "12.0",
        "status": "success",
        "message": "Job finished",
        "page_url": "https://version-12-0.string-db.org/cgi/globalenrichment?networkId=b9nIwzgFe2dz",
        "download_url": "https://version-12-0.string-db.org/api/tsv/downloadenrichmentresults?networkId=b9nIwzgFe2dz", ## available formats: [json/xml/tsv]
        "graph_url": "https://version-12-0.string-db.org/api/image/enrichmentfigure?networkId=b9nIwzgFe2dz" ## see enrichment visualization API for more settings
    }

]
Available parameters:
Parameter	Description
api_key	Required. API key used to authenticate the user (generated using get_api_key).
job_id	Job ID received after submitting a job (if not provided the method will print out all current and past jobs for the api_key/user)
Output fields:
Field	Description
job_id	The unique identifier of this analysis.
status	The current status of the job (e.g., queued, running, failed, success, etc.).
message	A description of the job's status, including the current step and the percentage of completion.
creation_time	Time of the submission in a format "YY-MM-DD HH:MM:SS"
page_url	(if finished) A link to access the final results of the Values/Ranks enrichment analysis directly on the STRING website.
download_url	(if finished) A link to download the enrichment results, covering all categories enriched in your data.
graph_url	(if finished) A link to an enrichment figure representing your data. For more details and figure customization options see Retrieving enrichment figure.
"page_url": "https://version-12-0.string-db.org/cgi/globalenrichment?networkId=b9nIwzgFe2dz",
Melanoma Values/Ranks enrichment page

"download_url": "https://version-12-0.string-db.org/api/tsv/downloadenrichmentresults?networkId=b9nIwzgFe2dz"
The results of the values/ranks enrichment analysis results include the following fields:

field	Description
Category	The high level category of the enriched term (GO Process, KEGG, Reactome etc.)
Term id	Identifier of the enriched term (e.g. GO:0042254, hsa00520)
Genes mapped	Number of proteins associated with this term in your input
Genes in set	Total number of proteins associated with this term (in and outside your input)
Enrichment score	The enrichment score quantifies how much the values associated with a term differ from the average value within your dataset. It is calculated by comparing the mean value of genes associated with a specific term to the greatest deviation from the overall input mean.
Direction	We assess enrichment at the top, bottom, and both ends of the dataset by folding the input values around the mean. This approach allows us to detect pathways where proteins exhibit significant changes in both directions, such as both upregulation and downregulation. The field indicates where the significant enrichment for a specific term was detected, specifying whether it was at the top, bottom, or both extremes of the distribution.
Count in set/pathway	The first number represents the count of proteins in your input that are annotated with a specific term. The second number shows the total count of proteins annotated with this term in the STRING database. It is imporant to note that the FDR calculation is based on the distribution of term values within your entire input, which serves as the background for this analysis. Anything outside your input does not influence the statistical tests used here.Therefore, the second number is provided solely for information and clarity.
False Discovery Rate	This metric assesses the significance of enrichment, displaying p-values that are adjusted for multiple testing within each category using the Benjamini–Hochberg procedure.
Method	The enrichment test used: afc (Aggregate Fold Change) or ks (Kolmogorov-Smirnov)—indicate the test used to derive the initial p-values. While the AFC test is more sensitive and thus suitable for detecting subtle variations, it is also computationally expensive. Therefore, for larger terms or terms with an unambiguous signal, we employ the KS method. Note that the choice of test has no bearing on the FDR calculation or its interpretation.
proteinIDs	Internal STRING identifier (e.g. 9606.ENSP00000269305) of proteins associated with the given term in your dataset.
proteinLabels	Canonical gene symbols of proteins associated with the given term in your dataset.
proteinInputLabels	Your query input identifiers (the identifiers you have used to query STRING) associated with the given term in your dataset.
proteinInputValues	The input values you have provided for the proteins associated with the given term.
proteinRanks	Ranks of the proteins associated with the given term based on your input value.
"graph_url": "https://version-12-0.string-db.org/api/image/enrichmentfigure?networkId=b9nIwzgFe2dz"
NOTE: For graph cusimazation options, including category, sorting, color and others see: retrieving enrichment figure.

Melanoma Values/Ranks enrichment figure

Remove a JobTop ↑
If you want to cancel or remove previously submitted or completed jobs you can use the the valuesranks_enrichment_remove method. This is useful if you realize there was an error in the submission, or you want to clean up the old analysis associated with the API key.

To remove a particular job_id you need to specify it. You can also remove all jobs associated with the api_key by assigning value all to the job_id parameter.

NOTE: Once removed the job_ids are not recorevable. NOTE: The removal of the job ids from the database does not delete the analysis data of the already completed jobs, and the links to the download and the webpage remain accessible.

Available parameters:
Parameter	Description
api_key	API key used to authenticate the user (generated once using get_api_key).
job_id	The job ID received after submitting a job (assign "all" to remove all your jobs associated with the api key)
Call:
https://version-12-0.string-db.org/api/json/valuesranks_enrichment_remove?api_key=[api_key]&job_id=[job_id]
Output example
[
    {
        "job_id": "job_id",
        "status": "removed", 
        "message": "job removed successfully.",
    }
]
