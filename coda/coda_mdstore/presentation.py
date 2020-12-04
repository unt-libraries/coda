import os
import re
import urllib.request
import urllib.parse
import requests
import zipstream

from bs4 import BeautifulSoup as BSoup
from codalib import APP_AUTHOR
from codalib.bagatom import (
    wrapAtom, ATOM, ATOM_NSMAP, BAG, BAG_NSMAP, TIME_FORMAT_STRING
)
from datetime import datetime
from lxml import etree
from pypairtree import pairtree

from . import exceptions
from coda_mdstore.models import Bag, Bag_Info, Node, External_Identifier

XHTML_NAMESPACE = "http://www.w3.org/1999/xhtml/"
XHTML = "{%s}" % XHTML_NAMESPACE
XHTML_NSMAP = {None: XHTML_NAMESPACE}


def getFileList(url):
    """
    Use BeautifulSoup to get a List of Files
    """

    fileList = []
    handle = urllib.request.urlopen(url)
    soup = BSoup(handle)
    trList = soup.find_all('tr')
    for tr in trList:
        tds = tr.find_all('td')
        for td in tds:
            anchors = td.find_all('a')
            for anchor in anchors:
                if anchor['href'][-1] == "/":
                    continue
                fileList.append(anchor['href'])
    return fileList


def getFileHandle(codaId, codaPath):
    """
    Attempt to get a urllib2 handle that we can read from based on a file
    specification
    """

    codaSplit = re.compile(r"ark:/\d+?/")
    codaPart = codaSplit.split(codaId, 1)[1]
    codaPairtree = pairtree.toPairTreePath(codaPart)
    codaPathParts = codaPath.split("/")
    for i in range(len(codaPathParts)):
        part = codaPathParts[i]
        codaPathParts[i] = urllib.parse.quote(part)
    escapedCodaPath = "/".join(codaPathParts)
    nodeList = Node.objects.all()
    exceptionList = []
    for node in nodeList:
        url_parts = urllib.parse.urlparse(node.node_url)
        url = urllib.parse.urljoin(
            "http://%s" % url_parts.hostname,
            os.path.join(
                url_parts.path,
                "store/pairtree_root",
                codaPairtree,
                codaPart,
                escapedCodaPath,
            )
        )
        try:
            fileHandle = urllib.request.urlopen(url)
            return fileHandle
        except Exception as e:
            exceptionList.append(str(e))
            pass
    raise Exception(
        "Unable to get handle for id %s at path %s" % (codaId, codaPath)
    )


def generateBagFiles(identifier, proxyRoot, proxyMode):
    """
    Return list of files in the bag
    """
    pathList = []
    transList = []
    handle = getFileHandle(identifier, "manifest-md5.txt")
    if not handle:
        raise Exception(
            "Unable to get handle for id %s" % (identifier)
        )
    bag_root = handle.url.rsplit('/', 1)[0]
    line = handle.readline()
    # iterate over handle and append urls to pathlist
    while line:
        line = line.strip()
        parts = line.split(None, 1)
        if len(parts) == 2:
            pathList.append(parts[1])
        line = handle.readline()
    # iterate top files and append to pathlist
    try:
        topFileHandle = getFileHandle(identifier, "")
        topFiles = getFileList(topFileHandle.url)
        for topFile in topFiles:
            pathList.append(topFile)
    except:
        pass
    # iterate pathlist and resolve a unicode path dependent on proxy mode
    for path in pathList:
        if isinstance(path, bytes):
            try:
                path = path.decode()
            except UnicodeDecodeError:
                path = path.decode('latin-1')

        # CODA_PROXY_MODE is a settings variable
        if proxyMode:
            uni = '%sbag/%s/%s' % (
                proxyRoot, identifier, path
            )
        else:
            uni = bag_root + "/" + path
        # throw the final path into a list
        transList.append(uni)

    return transList


def file_chunk_generator(url):
    """
    Download a file and stream it
    """
    r = requests.get(url, stream=True)
    if r.status_code != 200:
        return
    for chunk in r.iter_content(1024):
        yield chunk


def zip_file_streamer(urls, meta_id):
    """
    Stream zipped file using zipstream
    """
    with zipstream.ZipFile(mode='w') as zip_obj:
        for url in urls:
            filename = '%s/%s' % (meta_id, url.split(meta_id, 1)[-1])

            zip_obj.write_iter(filename, file_chunk_generator(url))

        # Each call will iterate the generator one at a time until all files are completed.
        for chunk in zip_obj:
            yield chunk


def bagSearch(bagString):
    """
    Search across all of the field_body fields in the Bag_Info objects and
    return a list of related bags
    """

    bagList = Bag.objects.filter(bag_info__field_body__search=bagString).distinct()
    if not bagList:
        bagList = Bag.objects.filter(name__search=bagString)
    return bagList


def makeBagAtomFeed(bagObjectList, id, title):
    """
    Given an iterable of bags, make an ATOM feed xml representation of it
    """

    feedTag = etree.Element(ATOM + "feed", nsmap=ATOM_NSMAP)
    idTag = etree.SubElement(feedTag, ATOM + "id")
    idTag.text = id
    titleTag = etree.SubElement(feedTag, ATOM + "title")
    titleTag.text = title
    etree.SubElement(feedTag, ATOM + "updated")
    linkTag = etree.SubElement(feedTag, ATOM + "link")
    linkTag.set("rel", "self")
    linkTag.set("href", id)
    for bagObject in bagObjectList:
        entryTag = wrapAtom(
            objectsToXML(bagObject), bagObject.name, bagObject.name,
            alt="/bag/" + bagObject.name
        )
        feedTag.append(entryTag)
    return feedTag


def updateBag(request):
    """
    updates a bag record with new information from an xml file
    """

    xmlText = request.body
    entryRoot = None
    entryRoot = etree.XML(xmlText)
    contentElement = entryRoot.xpath("*[local-name() = 'content']")[0]
    codaXML = contentElement.xpath("*[local-name() = 'codaXML']")[0]
    bag_name = codaXML.xpath("*[local-name() = 'name']")[0].text.strip()

    if bag_name not in request.path:
        raise exceptions.BadBagName('The bag name supplied in the URL does not match the XML')

    bag = Bag.objects.get(name=bag_name)

    # delete old info objects
    old_bag_infos = Bag_Info.objects.filter(bag_name=bag)
    old_bag_infos.delete()
    # delete old external id objects
    old_ext_ids = External_Identifier.objects.filter(belong_to_bag=bag)
    old_ext_ids.delete()
    # attempt to update a Bag object from the codaXML section
    bagObject, bagInfoObjectList, errorCode = xmlToBagObject(codaXML)
    bagObject.save()
    for bagInfoObject in bagInfoObjectList:
        bagInfoObject.save()
    return bagObject


def createBag(xmlText):
    """
    creates a bag from an xml document. returns a bag.
    """

    entryRoot = None
    entryRoot = etree.XML(xmlText)
    if entryRoot is None:
        raise Exception("Unable to parse uploaded XML")
    contentElement = entryRoot.xpath("*[local-name() = 'content']")[0]
    if contentElement is None:
        raise Exception("No content element located")
    codaXML = contentElement.xpath("*[local-name() = 'codaXML']")[0]
    codaName = codaXML.xpath("*[local-name() = 'name']")[0].text.strip()
    oldBagInfoObjectList = Bag_Info.objects.filter(bag_name=codaName)
    for oldBagInfoObject in oldBagInfoObjectList:
        oldBagInfoObject.delete()
    # attempt to create a Bag object from the codaXML section
    bagObject, bagInfoObjectList, errorCode = xmlToBagObject(codaXML)
    if errorCode:
        raise Exception("codaXML issue, %s" % (errorCode,))
    bagObject.save()
    for bagInfoObject in bagInfoObjectList:
        bagInfoObject.save()
    return bagObject, bagInfoObjectList


def xmlToBagObject(codaXML):
    """
    Take a codaXML element and turn it into a Bag object
    Returns (Bag object, list of Bag_Info objects, error code)
    """

    # first, let's get the bag name and see if it exists already
    try:
        name = codaXML.xpath("*[local-name() = 'name']")[0].text.strip()
        bagObject = Bag.objects.get(Bag, name=name)
    # if we can't get the object, then we're just making a new one.
    except Exception:
        bagObject = Bag()
    dateFormatString = "%Y-%m-%d"
    try:
        bagObject.name = codaXML.xpath(
            "*[local-name() = 'name']")[0].text.strip()
    except:
        return (None, None, "Unable to set 'name' attribute")
    try:
        bagObject.files = codaXML.xpath(
            "*[local-name() = 'fileCount']")[0].text.strip()
    except:
        return (None, None, "Unable to set 'files' attribute")
    try:
        bagObject.size = int(codaXML.xpath(
            "*[local-name() = 'payloadSize']")[0].text.strip())
    except Exception as e:
        return (None, None, "Unable to set 'size' attribute: %s" % (e,))
    try:
        bagObject.bagit_version = codaXML.xpath(
            "*[local-name()='bagitVersion']")[0].text.strip()
    except:
        pass
    try:
        bagObject.last_verified_date = datetime.strptime(
            codaXML.xpath(
                "*[local-name() = 'lastVerified']"
            )[0].text.strip(), dateFormatString
        )
    except:
        bagObject.last_verified_date = datetime.now()
    try:
        bagObject.last_verified_status = codaXML.xpath(
            "*[local-name() = 'lastStatus']")[0].text.strip()
    except:
        bagObject.last_verified_status = "pass"
    try:
        bagObject.bagging_date = datetime.strptime(
            codaXML.xpath(
                "*[local-name() = 'baggingDate']"
            )[0].text.strip(), dateFormatString
        )
    except:
        bagObject.bagging_date = datetime.now()
    bagInfo = codaXML.xpath("*[local-name() = 'bagInfo']")[0]
    if len(bagInfo):
        items = bagInfo.xpath("*[local-name() = 'item']")
    # make a list to store all the bag_info objects
    bagInfoObjects = []
    # iterate through items
    for item in items:
        bagInfoObject = Bag_Info()
        bagInfoObject.bag_name = bagObject
        try:
            bagInfoObject.field_name = item.xpath(
                "*[local-name() = 'name']")[0].text.strip()
            bagInfoObject.field_body = item.xpath(
                "*[local-name() = 'body']")[0].text.strip()
            if bagInfoObject.field_name == 'External-Identifier':
                extID = External_Identifier(
                    value=bagInfoObject.field_body,
                    belong_to_bag=bagInfoObject.bag_name,
                )
                extID.save()
        except:
            continue
        bagInfoObjects.append(bagInfoObject)
    return (bagObject, bagInfoObjects, None)


def objectsToXML(bagObject):
    """
    This is the reverse of xmlToObjects.  Given a "Bag" object, and a list of
    Bag_Info objects, it generates an XML object representative of such in the
    'codaXML' format.
    """

    codaXML = etree.Element(BAG + "codaXML", nsmap=BAG_NSMAP)
    name = etree.SubElement(codaXML, BAG + "name")
    name.text = bagObject.name
    fileCount = etree.SubElement(codaXML, BAG + "fileCount")
    fileCount.text = str(bagObject.files)
    payLoadSize = etree.SubElement(codaXML, BAG + "payloadSize")
    payLoadSize.text = str(bagObject.size)
    bagitVersion = etree.SubElement(codaXML, BAG + "bagitVersion")
    bagitVersion.text = bagObject.bagit_version
    try:
        lastVerified = etree.SubElement(codaXML, BAG + "lastVerified")
        lastVerified.text = str(bagObject.last_verified_date)
        lastStatus = etree.SubElement(codaXML, BAG + "lastStatus")
        lastStatus.text = bagObject.last_verified_status
    except:
        pass
    bagInfo = etree.SubElement(codaXML, BAG + "bagInfo")
    bagInfoObjectList = Bag_Info.objects.filter(bag_name=bagObject)
    for bagInfoObject in bagInfoObjectList:
        item = etree.SubElement(bagInfo, BAG + "item")
        nameTag = etree.SubElement(item, BAG + "name")
        nameTag.text = bagInfoObject.field_name
        bodyTag = etree.SubElement(item, BAG + "body")
        bodyTag.text = bagInfoObject.field_body
    return codaXML


def nodeEntry(node, webRoot=None):
    """
    Form an atom xml for a given node object.
    """

    nodeXML = etree.Element("node")
    node_name = etree.SubElement(nodeXML, "name")
    node_name.text = node.node_name
    node_capacity = etree.SubElement(nodeXML, "capacity")
    node_capacity.text = str(node.node_capacity)
    node_size = etree.SubElement(nodeXML, "size")
    node_size.text = str(node.node_size)
    node_path = etree.SubElement(nodeXML, "path")
    node_path.text = node.node_path
    node_url = etree.SubElement(nodeXML, "url")
    node_url.text = node.node_url
    node_last_checked = etree.SubElement(nodeXML, "last_checked")
    node_last_checked.text = node.last_checked.strftime(TIME_FORMAT_STRING)
    node_status = etree.SubElement(nodeXML, "status")
    node_status.text = node.get_status_display()
    atomXML = wrapAtom(
        xml=nodeXML,
        id='http://%s/node/%s/' % (webRoot, node.node_name),
        title=node.node_name,
        author=APP_AUTHOR['name'],
        author_uri=APP_AUTHOR['uri'],
    )
    return atomXML


def updateNode(request):
    """
    Parse the XML in a PUT request and update the node stat based on that
    """

    nodeXML = request.body
    entryRoot = etree.fromstring(nodeXML)
    contentElement = entryRoot.xpath("*[local-name() = 'content']")[0]
    nodeXML = contentElement.xpath("*[local-name() = 'node']")[0]
    node_name = nodeXML.xpath("*[local-name() = 'name']")[0].text.strip()

    if node_name not in request.path:
        raise exceptions.BadNodeName('The node name supplied in the URL does not match the XML')

    node = Node.objects.get(node_name=node_name)

    # we need capacity and size
    node_capacity = nodeXML.xpath(
        "*[local-name() = 'capacity']"
    )[0].text.strip()
    node_size = nodeXML.xpath("*[local-name() = 'size']")[0].text.strip()
    node_path = nodeXML.xpath("*[local-name() = 'path']")[0].text.strip()
    node_url = nodeXML.xpath("*[local-name() = 'url']")[0].text.strip()
    node.node_capacity = int(node_capacity)
    node.node_size = int(node_size)
    node.node_path = node_path
    node.node_name = node_name
    node.node_url = node_url
    # last_checked most likely will be passed in via the GET > PUT discussions
    # but will always be overwritten.
    node.last_checked = datetime.now()
    return node


def createNode(request):
    """
    Parse the XML in a POST request and create the node stat based on that
    """

    nodeXML = request.body
    entryRoot = etree.fromstring(nodeXML)
    contentElement = entryRoot.xpath("*[local-name() = 'content']")[0]
    nodeXML = contentElement.xpath("*[local-name() = 'node']")[0]
    node_name = nodeXML.xpath("*[local-name() = 'name']")[0].text.strip()
    node_capacity = nodeXML.xpath(
        "*[local-name() = 'capacity']"
    )[0].text.strip()
    node_size = nodeXML.xpath("*[local-name() = 'size']")[0].text.strip()
    node_path = nodeXML.xpath("*[local-name() = 'path']")[0].text.strip()
    node_url = nodeXML.xpath("*[local-name() = 'url']")[0].text.strip()
    node = Node()
    node.node_capacity = int(node_capacity)
    node.node_size = int(node_size)
    node.node_path = node_path
    node.node_name = node_name
    node.node_url = node_url
    node.last_checked = datetime.now()
    return node
