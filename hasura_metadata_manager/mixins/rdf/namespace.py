from rdflib import Namespace

NS_HASURA = Namespace("http://hasura.com/ontology/")
NS_HASURA_PROP = Namespace("http://hasura.com/ontology/property#")
NS_HASURA_REL = Namespace("http://hasura.com/ontology/relationship#")
NS_HASURA_OBJ_REL = Namespace("http://hasura.com/ontology/ObjectRelationship#")
NS_HASURA_MODEL = Namespace("http://hasura.com/ontology/model#")


def bind_namespaces(graph):
    graph.bind("has", NS_HASURA)
    graph.bind("prop", NS_HASURA_PROP)
    graph.bind("rel", NS_HASURA_REL)
    graph.bind("drel", NS_HASURA_OBJ_REL)
    graph.bind("mod", NS_HASURA_MODEL)
