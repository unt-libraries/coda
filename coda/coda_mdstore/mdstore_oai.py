from coda_mdstore.models import Bag, Bag_Info
from coda_mdstore.views import objectsToXML
from oaipmh import common, error
from datetime import datetime


class OAIInterface(object):
    """
    This class implements the IOAI 'interface', laid out here:

     https://github.com/infrae/pyoai/blob/master/src/oaipmh/interfaces.py
    """
    def __init__(self, identifyDict={}, resultSize=10, domain="", debug=False):
        self.identifyDict = {
            'repositoryName': 'Base',
            # 'baseURL':'http://texashistory.unt.edu/search/oai/',
            'baseURL': 'http://not.a.good.base.url.com/fixit/kurt/',
            'protocolVersion': "2.0",
            'adminEmails': ['not.a.real.email@.fixit.kurt.com'],
            'earliestDatestamp': datetime(2004, 05, 19),
            'deletedRecord': 'transient',
            'granularity': 'YYYY-MM-DDThh:mm:ssZ',
            # 'granularity':'YYYY-MM-DD',
            'compression': ['identity'],
        }
        if identifyDict:
            self.identifyDict.update(identifyDict)
        self.resultSize = resultSize
        self.timeFormatString = "%Y-%m-%d"
        self.debug = debug
        self.domain = domain

    def identify(self):
        return common.Identify(**self.identifyDict)

    def getRecord(self, metadataPrefix, identifier):
        """
        Get a record from django and format it
        """
        bagObject = None
        id = infoToArk(identifier)
        try:
            bagObject = Bag.objects.get(name=id)
        except Bag.DoesNotExist:
            raise error.IdDoesNotExistError, "Id doesnt exist: %s" % identifier
        record = makeDataRecord(
            bagObject, domain=self.domain,
            metadataPrefix=metadataPrefix
        )
        return record

    def listSets(self, cursor=0, batch_size=10):
        """
        No sets as of yet
        """
        raise error.NoSetHierarchyError

    def listMetadataFormats(self, identifier=None):
        if identifier:
            id = infoToArk(identifier)
            try:
                Bag.objects.get(name=id)
            except Bag.DoesNotExist:
                raise error.IdDoesNotExistError(
                    "Id does not exist: %s, (%s)" % (identifier, id)
                )
        return [
                    (
                        'oai_dc',
                        'http://www.openarchives.org/OAI/2.0/OAI-PMH.xsd',
                        'http://www.openarchives.org/OAI/2.0/oai_dc/'
                    ),
                    (
                        'coda_bag',
                        'http://digital2.library.unt.edu/bagxml.xsd',
                        'http://digital2.library.unt.edu/coda/bagxml/'
                    ),
                ]

    def listIdentifiers(self, metadataPrefix=None, from_=None, until=None,
                        set=None, cursor=0, batch_size=10):

        return self.makeList(
            metadataPrefix=metadataPrefix, from_=from_,
            until=until, set=set, cursor=cursor, batch_size=batch_size,
            headersOnly=True
        )

    def listRecords(self, metadataPrefix=None, from_=None, until=None,
                    set=None, cursor=0, batch_size=10):

        return self.makeList(
            metadataPrefix=metadataPrefix, from_=from_,
            until=until, set=set, cursor=cursor, batch_size=batch_size,
            headersOnly=False
        )

    def makeList(self, metadataPrefix=None, from_=None, until=None,
                 set=None, cursor=0, batch_size=10, headersOnly=True):
        """
        Assuming that from_ and until_ are datetime.datetime objects
        """

        # valid metadata prefixes only
        formatString = "%Y-%m-%d"
        validPrefixes = ('oai_dc', 'coda_bag')
        if metadataPrefix:
            if metadataPrefix not in validPrefixes:
                raise error.CannotDisseminateFormatError(
                    "Metadata Prefix %s is not supported" % (metadataPrefix,)
                )
        # let's make some defaults
        fromValue = datetime(1900, 1, 1, 0, 0, 0)
        if from_:
            fromValue = from_
        untilValue = datetime.utcnow()
        if until:
            untilValue = until
        fromString = fromValue.strftime(formatString)
        untilString = untilValue.strftime(formatString)
        bagObjectList = Bag.objects.filter(
            bagging_date__lte=untilString).filter(bagging_date__gte=fromString)
        listLength = bagObjectList.count()
        if cursor + batch_size >= listLength:
            resultSet = bagObjectList[cursor:]
        else:
            resultSet = bagObjectList[cursor:cursor + batch_size]
        resultList = []
        for result in resultSet:
            record = makeDataRecord(
                result, domain=self.domain,
                metadataPrefix=metadataPrefix
            )
            if headersOnly:
                resultList.append(record[0])
            else:
                resultList.append(record)
        return resultList


def makeDataRecord(
    bagObject,
    domain="",
    metadataPrefix="oai_dc",
    setAssociationList=[]
):
    """
    Given a Bag object, make a record in the format that oaipmh uses
    """

    # to build the header, we need the unique ID, and the datestamp
    # would the setspec be taken from facets?
    bagInfoObjectList = Bag_Info.objects.filter(bag_name=bagObject)

    id = arkToInfo(bagObject.name)
    date = bagObject.bagging_date
    for bagInfoObject in bagInfoObjectList:
        if bagInfoObject.field_name == 'Bagging-Date':
            formatString = "%Y-%m-%d"
            baggingDate = bagInfoObject.field_body
            try:
                date = datetime.strptime(baggingDate, formatString)
            except:
                pass
            break
    date = date.replace(microsecond=0, tzinfo=None)
    bagInfoDict = {}
    for bagInfoObject in bagInfoObjectList:
        bagInfoDict[bagInfoObject.field_name] = bagInfoObject.field_body
    stripdomain = domain
    if stripdomain.startswith("http://"):
        stripdomain = stripdomain[len("http://"):]
    dcDict = {}
    identifiers = [bagObject.name]
    if "External-Identifier" in bagInfoDict:
        identifiers.append(bagInfoDict["External-Identifier"])
    dcDict["identifier"] = identifiers
    if "Contact-Name" in bagInfoDict:
        dcDict["creator"] = [bagInfoDict["Contact-Name"]]
    if "External-Description" in bagInfoDict:
        dcDict["description"] = [bagInfoDict["External-Description"]]
    if "Bagging-Date" in bagInfoDict:
        dcDict["date"] = [bagInfoDict["Bagging-Date"]]
    if not len(dcDict):
        raise Exception("dcDict is empty")
    setList = []
    header = common.Header(
        id,
        date,
        setList,
        False,
    )
    dublinStruct = dcDict
    if metadataPrefix == "oai_dc":
        metadata = common.Metadata(dublinStruct)
    elif metadataPrefix == "coda_bag":
        bagMap = {}
        bagMap["bag"] = bagObject
        metadata = common.Metadata(bagMap)
    return (header, metadata, None)


def arkToInfo(ark):
    """
    Turn an ark id into an info: uri
    """

    parts = ark.split("ark:", 1)
    if len(parts) != 2:
        return ark
    return "info:ark%s" % parts[1]


def infoToArk(info):
    """
    Guess
    """

    parts = info.split("info:ark", 1)
    if len(parts) != 2:
        return info
    return "ark:%s" % parts[1]


def coda_bag_writer(element, metadata):
    map = metadata.getMap()
    codaXML = objectsToXML(map["bag"])
    element.append(codaXML)
