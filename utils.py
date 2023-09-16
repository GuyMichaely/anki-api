from itertools import chain
def invert_dict(d):
  return {sub_item: key for key, item in d.items() for sub_item in item}
def flatten(l):
  return list(chain(*l))
