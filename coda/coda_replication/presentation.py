from codalib.bagatom import getValueByName, getNodeByName
from coda_replication.models import QueueEntry
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from datetime import datetime
from lxml import etree

TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def xmlToQueueEntry(queue_xml):
    """Convert XML to a QueueEntry object."""

    ark = getValueByName(queue_xml, "ark")
    bytes_, files = getValueByName(queue_xml, "oxum").split('.')
    url_list = getValueByName(queue_xml, "urlListLink")
    status = getValueByName(queue_xml, "status")

    # The next three assignment statement groupings protect against converting
    # a possible None or empty string return value to another type,
    # which could result in an exception.
    queue_position = getValueByName(queue_xml, "position")
    queue_position = int(queue_position) if queue_position else None

    harvest_start = getValueByName(queue_xml, "start")
    harvest_start = datetime.strptime(harvest_start, TIME_FORMAT) if harvest_start else None

    harvest_end = getValueByName(queue_xml, "end")
    harvest_end = datetime.strptime(harvest_end, TIME_FORMAT) if harvest_end else None

    return QueueEntry(
        ark=ark,
        bytes=bytes_,
        files=files,
        url_list=url_list,
        status=status,
        queue_position=queue_position,
        harvest_start=harvest_start,
        harvest_end=harvest_end)


def addQueueEntry(rawXML):
    """
    Handle adding the Queue.  Based on XML input.
    """
    entryRoot = etree.fromstring(rawXML)
    contentElement = getNodeByName(entryRoot, "content")
    queueEntryNode = getNodeByName(contentElement, "queueEntry")
    newEntry = xmlToQueueEntry(queueEntryNode)
    queueList = QueueEntry.objects.order_by("-queue_position")
    try:
        highPosition = queueList[0].queue_position
    except IndexError:
        highPosition = 0
    newEntry.queue_position = highPosition + 1
    newEntry.status = "1"
    newEntry.save()
    return newEntry


def updateQueueEntry(rawXML, validate_ark=None):
    """
    Handle updating the Queue.  Based on XML input.
    """

    updateList = [
        "oxum",
        "url_list",
        "status",
        "harvest_start",
        "harvest_end",
        "queue_position",
    ]
    entryRoot = etree.fromstring(rawXML)
    contentElement = getNodeByName(entryRoot, "content")
    queueEntryNode = getNodeByName(contentElement, "queueEntry")
    newEntry = xmlToQueueEntry(queueEntryNode)
    if validate_ark and newEntry.ark != validate_ark:
        raise ValidationError("Mismatch between URL identifier and document ID.")
    try:
        oldEntry = QueueEntry.objects.get(ark=newEntry.ark)
    except QueueEntry.DoesNotExist:
        raise ObjectDoesNotExist(
            "There is no existing Queue Entry for ark '%s'." % newEntry.ark
        )
    for item in updateList:
        if hasattr(oldEntry, item) and getattr(oldEntry, item):
            if not hasattr(newEntry, item) or not getattr(newEntry, item):
                setattr(newEntry, item, getattr(oldEntry, item))
    oldEntry.delete()
    newEntry.save()
    return newEntry
