import io,unittest
from unittest.mock import patch
from fastapi import HTTPException
from pypdf import PdfWriter
from pypdf.generic import DictionaryObject,NameObject,DecodedStreamObject
from app.services.syllabus_processing import process_pdf,propose_pages

def text_pdf(lines,encrypted=False):
 writer=PdfWriter();page=writer.add_blank_page(width=600,height=800)
 font=DictionaryObject({NameObject('/Type'):NameObject('/Font'),NameObject('/Subtype'):NameObject('/Type1'),NameObject('/BaseFont'):NameObject('/Helvetica')})
 page[NameObject('/Resources')]=DictionaryObject({NameObject('/Font'):DictionaryObject({NameObject('/F1'):writer._add_object(font)})})
 content=DecodedStreamObject();commands=['BT /F1 12 Tf 40 760 Td']
 for line in lines:commands.append('('+line.replace('\\','\\\\').replace('(','\\(').replace(')','\\)')+') Tj 0 -18 Td')
 commands.append('ET');content.set_data('\n'.join(commands).encode('ascii'));page[NameObject('/Contents')]=writer._add_object(content)
 if encrypted:writer.encrypt('test')
 stream=io.BytesIO();writer.write(stream);return stream.getvalue()

class SyllabusProcessingTests(unittest.TestCase):
 def test_explicit_hierarchy_evidence_and_unassigned_text(self):
  text,proposal=process_pdf(text_pdf(['Course: Operating Systems','Course code: CS301','Unit 1: Memory','Topic: Paging','Objectives: Explain page tables','Subtopics: TLB; frames','Unstructured paragraph to review']))
  subject=proposal['subjects'][0];topic=subject['children'][0]['children'][0]
  self.assertEqual(subject['code'],'CS301');self.assertEqual(topic['title'],'Paging')
  self.assertEqual(topic['subtopics'],['TLB','frames']);self.assertEqual(proposal['evidence'][0]['page'],1)
  self.assertEqual(proposal['unparsed'][0]['text'],'Unstructured paragraph to review')
  self.assertIn('Unstructured paragraph',text)
 def test_ambiguous_text_does_not_invent_subjects_or_topics(self):
  result=propose_pages(['An introduction to operating systems\nMemory is useful\nUnit 1: Orphan unit',''])
  self.assertEqual(result['subjects'],[]);self.assertEqual(len(result['unparsed']),3)
  self.assertTrue(any('Page 2' in warning for warning in result['warnings']))
 def test_malformed_encrypted_scanned_and_size_limits(self):
  writer=PdfWriter();writer.add_blank_page(width=100,height=100);buf=io.BytesIO();writer.write(buf)
  for contents in [b'not a pdf',b'%PDF-broken',buf.getvalue(),text_pdf(['Course: CS'],True)]:
   with self.assertRaises(HTTPException):process_pdf(contents)
  with patch('app.services.syllabus_processing.MAX_BYTES',10):
   with self.assertRaises(HTTPException) as error:process_pdf(text_pdf(['Course: CS']))
   self.assertEqual(error.exception.status_code,413)
