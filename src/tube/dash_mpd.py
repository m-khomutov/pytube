import xml.etree.ElementTree as xmlTree
from datetime import timedelta


class DashMpd:
    def __init__(self, title_text, duration, max_segment_duration, adaptation_sets):
        dt = str(timedelta(seconds=duration)).split(':')
        duration = f'PT{dt[0]}H{dt[1]}M{dt[2]}S'
        self._value = xmlTree.Element('MPD')
        self._value.set('xmlns', 'urn:mpeg:dash:schema:mpd:2011')
        self._value.set('minBufferTime', 'PT1.500S')
        self._value.set('type', 'static')
        self._value.set('mediaPresentationDuration', duration)
        dt = str(timedelta(seconds=max_segment_duration)).split(':')
        self._value.set('maxSegmentDuration', f'PT{dt[0]}H{dt[1]}M{dt[2]}S')
        self._value.set('profiles', 'urn:mpeg:dash:profile:full:2011')
        info = xmlTree.SubElement(self._value, 'ProgramInformation')
        info.set('moreInformationURL', 'https://github.com/m-khomutov/pyfmp4')
        title = xmlTree.SubElement(info, 'Title')
        title.text = title_text
        period = xmlTree.SubElement(self._value, 'Period')
        period.set('duration', duration)
        for adaptation in adaptation_sets:
            adaptation_set = xmlTree.SubElement(period, 'AdaptationSet')
            adaptation_set.set('segmentAlignment', 'true')
            adaptation_set.set('lang', adaptation.language)
            representation = xmlTree.SubElement(adaptation_set, 'Representation')
            representation.set('id', str(adaptation.id))
            representation.set('mimeType', adaptation.mime_type)
            segment_template = xmlTree.SubElement(representation, 'SegmentTemplate')
            segment_template.set('timescale', str(adaptation.timescale))
            segment_template.set('media', adaptation.media)
            segment_template.set('startNumber', '0')
            segment_template.set('duration', str(adaptation.duration))
            segment_template.set('initialization', adaptation.initialization)

    def __str__(self):
        """Returns prepared DASH MPD"""
        return xmlTree.tostring(self._value, encoding='utf-8', xml_declaration=True).decode('utf-8')
