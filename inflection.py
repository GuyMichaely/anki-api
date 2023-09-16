import pymorphy2, unicodedata

pymorphy2_parse = pymorphy2.MorphAnalyzer().parse
from pymorphy2.tagset import OpencorporaTag
from utils import *
from enum import Enum
from operator import attrgetter
from abc import ABC, abstractmethod
from collections import namedtuple
from itertools import chain

GRAMMEME_TYPES = {
    'ANIMACY': 'animacy',
    'ASPECTS': 'aspect',
    'CASES': 'case',
    'GENDERS': 'gender',
    'INVOLVEMENT': 'involvement',
    'MOODS': 'mood',
    'NUMBERS': 'number',
    'PARTS_OF_SPEECH': 'POS',
    'PERSONS': 'person',
    'TENSES': 'tense',
    'TRANSITIVITY': 'transitivity',
    'VOICES': 'voice'
}  # maps OpencorporaTag grammeme types to the attribute name to access the given grammeme on a OpencorporaTag instance
GRAMMEME_VALUE_TO_ACCESSOR = invert_dict({
    GRAMMEME_TYPES[grammeme_type]: getattr(OpencorporaTag, grammeme_type)
    for grammeme_type in GRAMMEME_TYPES.keys()
})

class InflectableWord(ABC):
  InflectionsGroupedByNumber = namedtuple('Inflections', 'singular plural')
  NameAndSortKey = namedtuple('NameAndSort', 'name sortKey') # name is string[], a list of grammeme vectors where a grammeme vector is a '*' delimited string of grammeme values
  NameAndSortKeyGroupedByNumber = namedtuple('NameAndSortGroupedByNumber', 'singular plural')
  FormatCommaData = namedtuple('FormatCommaData', 'format data')
  @abstractmethod
  def _getAllInflections(self) -> InflectionsGroupedByNumber:
    pass
    
  # returns pymorphy2 parse
  @abstractmethod
  def inflect(self, grammemes):
    pass
    
  @staticmethod
  def getGetName(accessors):
    def getName(inflection): 
      return '*'.join([getattr(inflection.tag, accessor) for accessor in accessors])
    return getName
  
  # inflections is a list of pymorphy2 parses
  @staticmethod
  def generateNameAndSortKey(inflections) -> NameAndSortKey:
    arbitraryInflection = inflections[0]
    accessors = {GRAMMEME_VALUE_TO_ACCESSOR[v] for v in arbitraryInflection.tag.grammemes} # assumes that all the inflections have the same grammeme fields
    for accessor in accessors.copy():
      accessorDomain = {getattr(inflection.tag, accessor) for inflection in inflections}
      if len(accessorDomain) == 1:
        accessors.remove(accessor)
    varyingAccessors = sorted(accessors) # sorting in case order of accessors differs for words which should have the same inflection types

    getName = InflectableWord.getGetName(varyingAccessors)
    return InflectableWord.NameAndSortKey(sorted(map(getName, inflections)), getName) # TODO: make the sorted(map(...)) an ordered set?
    
  def getAllInflections(self):
    # returns FormatCommaData[2]
    inflectionsGroupedByNumber = self._getAllInflections()
    print(f'{inflectionsGroupedByNumber=}')
    nameAndSortKeyGroupedByNumber = InflectableWord.NameAndSortKeyGroupedByNumber(*map(InflectableWord.generateNameAndSortKey, inflectionsGroupedByNumber))
    
    nameGroupedByNumber = (nameAndSortKey.name for nameAndSortKey in nameAndSortKeyGroupedByNumber)
    
    sortKeyGroupedByNumber = (nameAndSortKey.sortKey for nameAndSortKey in nameAndSortKeyGroupedByNumber)
    sortedWordsGroupedByNumber = (map(attrgetter('word'), sorted(inflections, key=sortKey)) for inflections, sortKey in zip(inflectionsGroupedByNumber, sortKeyGroupedByNumber))
    
    return map(InflectableWord.FormatCommaData, zip(nameGroupedByNumber, sortedWordsGroupedByNumber))

class Noun(InflectableWord):
  def _getAllInflections(self):
    print(f'executing _getAllInflections in {self.__class__.__name__}')
    return InflectableWord.InflectionsGroupedByNumber(*map(self.getAllInflectionsForNumber, OpencorporaTag.NUMBERS))

  def getAllInflectionsForNumber(self, number):
    inflectionsForCase = {case: self.inflect({number} | set(case.split(','))) for case in chain(self.cases, self.rare_cases)}
    print(f'{inflectionsForCase=}')
    for rare_case, normal_case in self.rare_cases.items():
      if inflectionsForCase[rare_case] == inflectionsForCase[normal_case]:
        print(f'deleting {rare_case=}')
        del inflectionsForCase[rare_case]
    print(f'after deletion: {inflectionsForCase=}')
    return list(inflectionsForCase.values())

class SingleAnimacyNoun(Noun):
  def __init__(self, parse):
    self.word = parse
    self.cases, self.rare_cases = OpencorporaTag.CASES, OpencorporaTag.RARE_CASES

  def inflect(self, grammemes):
    print(f'inflecting {self.word.word} for {grammemes=}')
    return self.word.inflect(grammemes)

class MultiAnimacyNoun(Noun):
  def __init__(self, parse1, parse2):
    self.anim, self.inan = parse1, parse2
    if self.anim.tag.animacy == 'inan':
      self.anim, self.inan = self.inan, self.anim

    self.cases = list(OpencorporaTag.CASES)
    self.cases.remove('accs')
    self.cases += ['accs,anim', 'accs,inan']
    self.rare_cases = OpencorporaTag.RARE_CASES.copy()
    del self.rare_cases['acc1']
    del self.rare_cases['acc2']
    self.rare_cases['acc1,anim'] = 'accs,anim'
    self.rare_cases['acc2,anim'] = 'accs,anim'
    self.rare_cases['acc1,inan'] = 'accs,inan'
    self.rare_cases['acc2,inan'] = 'accs,inan'

  def inflect(self, grammemes):
    if 'inan' in grammemes:
      return self.inan.inflect(grammemes)
    return self.anim.inflect(grammemes)

def getNounInflections(baseWordParses):
  if not all(p.tag.animacy == baseWordParses[0].tag.animacy for p in baseWordParses[1:]):
    noun = MultiAnimacyNoun(*baseWordParses)
  else:
    noun = SingleAnimacyNoun(baseWordParses[0])
  return noun.getAllInflections()

# returns (True, InflectableWord.FormatCommaData[2]) | (False, parse[])
def getAllInflections(word, grammemeString):
  baseWordParses = determineBaseWords(word, grammemeString)
  if not uniqueBases(baseWordParses):
    return False, baseWordParses
    
  POS_MAP = invert_dict({
    'Adj': ['ADJF', 'ADJS', 'NUMR', 'COMP', 'ADVB'],
    'Noun': ['NOUN', 'NPRO','PRTS', 'PRTF'],
    'Verb': ['VERB', 'GRND']
  })
  POS = POS_MAP[baseWordParses[0].tag.POS]
  return True, eval(f'get{POS}Inflections')(baseWordParses)

def removeDiacritics(text):
  return "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))

def uniqueBases(parses):
  if parses[0].tag.POS in ['NOUN', 'NPRO']:
    return len({(p.word, p.tag.animacy) for p in parses}) <= 2
  return len({(p.word, p.tag.POS) for p in parses}) == 1

def determineBaseWords(word, grammemeString):
  word = removeDiacritics(word)
  grammemes = set(grammemeString.split(',')) if grammemeString else set()
  parses = pymorphy2_parse(word)
  normalForms = [p.normalized for p in parses]
  return [p for p in normalForms if grammemes.issubset(p.tag.grammemes)]