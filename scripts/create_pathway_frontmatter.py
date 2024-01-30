import csv
from datetime import date
import frontmatter
from frontmatter.default_handlers import YAMLHandler
from io import BytesIO
import json
from pathlib import Path
import re
import sys


DATASOURCE_RE = re.compile(r'http://purl.obolibrary.org/obo/([A-Z]+)_\d+')
WPID__PR_RE = re.compile(r'.*(WP\d+__PR\d+).*')
WPID_RE = re.compile(r'.*(WP\d+).*')

ANNOTION_TYPE_BY_NAMESPACE = {
        'PW': 'Pathway Ontology',
        'CL': 'Cell Type Ontology',
        'DOID': 'Disease Ontology',
        }

parent_annotation_iris_by_datasource = {}
with open('./annotations/top_parent_terms.json') as f:
    top_parent_terms = json.load(f)
    for datasource,ontology_ids in top_parent_terms.items():
        if not datasource in parent_annotation_iris_by_datasource:
            parent_annotation_iris_by_datasource[datasource] = set()
        iris = parent_annotation_iris_by_datasource[datasource]
        for ontology_id in ontology_ids:
            datasource, id_number = ontology_id.split(':', 1)
            iris.add('http://purl.obolibrary.org/obo/' + datasource + '_' + id_number)

supported_datasources = set(parent_annotation_iris_by_datasource.keys())


def get_datasource(iri):
    m = DATASOURCE_RE.fullmatch(iri)
    if m:
        return m.group(1)

def get_wpid_pr(input_str):
    m = WPID__PR_RE.match(input_str)
    if m:
        return m.group(1)

def get_wpid(input_str):
    m = WPID_RE.match(input_str)
    if m:
        return m.group(1)

def get_annotation_details(iri):
    datasource = get_datasource(iri)
    with open('./annotations/' + datasource + '.csv') as f:
        reader = csv.DictReader(f)
        for l in reader:
            if l['Class ID'] == iri:
                return l

def parse_parent_parent_iri(raw_parent_iri):
    parent_iris = []
    for raw_parent_iri in raw_parent_iri.strip().split('|'):
        parent_iri = raw_parent_iri.strip()
        datasource = get_datasource(parent_iri)
        if datasource in supported_datasources:
            parent_iris.append(parent_iri)
    return parent_iris

# TODO: what's the difference between the key 'Parents' and
# the key 'http://data.bioontology.org/metadata/treeView'?
def get_parent_annotation_preferred_label(parent_iri, child_iri = ''):
    datasource = get_datasource(parent_iri)

    if (not parent_iri) or (parent_iri == child_iri):
        return None

    if parent_iri in parent_annotation_iris_by_datasource[datasource]:
        annotation_details = get_annotation_details(parent_iri)
        return annotation_details['Preferred Label']

    annotation_details = get_annotation_details(parent_iri)

    for grandparent_iri in parse_parent_parent_iri(annotation_details['Parents']):
        preferred_label = get_parent_annotation_preferred_label(
                grandparent_iri,
                parent_iri)
        if preferred_label:
            return preferred_label 


info_f = sys.argv[1]
if not info_f:
    raise Exception('No info_f provided')

info_fp = Path(info_f)
wpid_pr = get_wpid_pr(info_fp.stem)
wpid = get_wpid(info_fp.stem)
if not wpid:
    raise Exception('Cannot extract WikiPathways ID from ' + info_f)

#frontmatter_fp = Path('./pathways/' + wpid + '/' + wpid + '.md')
frontmatter_fp = Path('./' + wpid_pr + '.md')
frontmatter_f = str(frontmatter_fp)
if frontmatter_fp.exists():
    post = frontmatter.load(frontmatter_f, handler=YAMLHandler())
else:
    # TODO: is there a better way to create an empty post object?
    post = frontmatter.loads('---\n---')

with open(info_f) as f:
        parsed_metadata = json.load(f)

if not 'title' in parsed_metadata:
    parsed_metadata['title'] = ''
if not 'description' in parsed_metadata:
    parsed_metadata['description'] = ''
if not 'revision' in parsed_metadata:
    parsed_metadata['revision'] = None

# Add in communities
communities_by_wpid = dict()
for p in sorted(Path('./').joinpath('communities/').glob('**/*.txt')):
    community = p.stem
    with p.open() as f:
        for id in f.read().splitlines():
            if not id in communities_by_wpid:
                communities_by_wpid[id] = list()
            communities_by_wpid[id].append(community)

communities = communities_by_wpid.get(wpid, list())
post['communities'] = communities

# Add in NDEx UUID
ndex_by_wpid = {}
with open(Path('./').joinpath('downstream/ndex_lookup.csv')) as f:
    reader = csv.DictReader(f)
    for row in reader:
        ndex_by_wpid[row['wpid']] = row['ndexid']

ndex = ndex_by_wpid.get(wpid)
post['ndex'] = ndex

# Add in citedIn
ci_path = Path('./').joinpath('downstream/citedin_lookup.yml')
citedin_lookup = frontmatter.load(str(ci_path), handler=YAMLHandler())
citedin = citedin_lookup.get(wpid, str())
post['citedin'] = citedin

for key, value in parsed_metadata.items():
    if key == 'ontology-ids':
        annotations = []
        for ontology_id in value:
            datasource, id_number = ontology_id.split(':', 1)

            annotation = {
                    'id': ontology_id,
                    'type': ANNOTION_TYPE_BY_NAMESPACE[datasource]
                    }

            annotations.append(annotation)

            iri = 'http://purl.obolibrary.org/obo/' + datasource + '_' + id_number
            annotation_details = get_annotation_details(iri)
            if annotation_details:
                annotation['value'] = annotation_details['Preferred Label']
                parent = get_parent_annotation_preferred_label(iri)
                if parent:
                    annotation['parent'] = parent

        post['annotations'] = annotations
    elif key == 'last-edited':
        if len(value) == 8: # 20210601
            post[key] = date(int(value[0:4]), int(value[4:6]), int(value[6:8]))
        elif len(value) == 10: #2020-06-01
            post[key] = date(int(value[0:4]), int(value[5:7]), int(value[8:10]))
        else:
            raise Exception('Unexpected date value: ' + value)
    else:
        post[key] = value

datanode_labels = set()
#with open('./pathways/' + wpid + '/' + wpid + '-datanodes.tsv') as f:
with open('./' + wpid_pr + '-datanodes.tsv') as f:
    reader = csv.DictReader(f, delimiter="\t", quoting=csv.QUOTE_NONE)
    for line in reader:
        datanode_labels.add(line['Label'])

# TODO: Tina will add this.
#post['github-authors'] = []

post['redirect_from'] = [
    '/index.php/Pathway:' + wpid_pr,
    '/instance/' + wpid_pr,
]
if 'revision' in post and (not post['revision'] is None):
    post['redirect_from'].append(
            '/instance/' + wpid_pr + '_' + post['revision']
            )

post['seo'] = 'CreativeWork'

post['schema-jsonld'] = [{
    '@context': 'https://schema.org/',
    '@id': 'https://wikipathways.github.io/pathways/' + wpid_pr + '.html',
    '@type': 'Dataset',
    'name': post['title'],
    'description': post['description'],
    'license': 'CC0',
    'creator': {'@type': 'Organization', 'name': 'WikiPathways'},
    'keywords': sorted(datanode_labels),
}]

with open(frontmatter_f, 'wb') as f:
    frontmatter.dump(post, f)
