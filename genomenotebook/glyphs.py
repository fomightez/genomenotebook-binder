# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/API/02_glyphs.ipynb.

# %% auto 0
__all__ = ['Y_RANGE', 'default_glyphs', 'get_y_range', 'arrow_coordinates', 'box_coordinates', 'Glyph', 'get_default_glyphs',
           'get_patch_coordinates', 'get_feature_name', 'get_feature_patches']

# %% ../nbs/API/02_glyphs.ipynb 5
import numpy as np
import pandas as pd
import io

from bokeh.plotting import figure
from bokeh.models.tools import BoxZoomTool
from bokeh.models import HoverTool, NumeralTickFormatter, LabelSet
from bokeh.models.glyphs import Patches
from bokeh.models import (
    CustomJS,
    Range1d,
    ColumnDataSource,
)
from .data import get_example_data_dir
from genomenotebook.utils import (
    parse_gff,
    default_types,
    default_attributes,
)

from collections import defaultdict
import os
from typing import *
import copy

# %% ../nbs/API/02_glyphs.ipynb 6
from collections import defaultdict

# %% ../nbs/API/02_glyphs.ipynb 7
Y_RANGE = (0, 1)
def get_y_range() -> tuple:
    """Accessor that returns the Y range for the genome browser plot
    """
    return Y_RANGE

# %% ../nbs/API/02_glyphs.ipynb 8
def arrow_coordinates(feature, 
                      height: float = 1, #relative height of the feature (between 0 and 1)
                      feature_height: float = 0.15, #fraction of the annotation track occupied by the feature glyphs
                      ):
    
    feature_size = feature.right - feature.left
    
    if feature.strand=="+":
        arrow_base = feature.end - np.minimum(feature_size, 100)
    else:
        arrow_base = feature.end + np.minimum(feature_size, 100)
    
    xs=(feature.start,
        feature.start,
        arrow_base,
        feature.end,
        arrow_base
       )
    
    offset=feature_height*(1-height)/2
    y_min = 0.05+offset
    y_max = 0.05+feature_height-offset
    ys = (y_min, y_max, y_max, (y_max + y_min) / 2, y_min)
    return xs, ys


# %% ../nbs/API/02_glyphs.ipynb 9
def box_coordinates(feature, 
                    height: float = 1, #relative height of the feature (between 0 and 1)
                    feature_height: float = 0.15, #fraction of the annotation track occupied by the feature glyphs
                    ):
    xs=(feature.left, feature.left,
        feature.right, feature.right)
    
    offset=feature_height*(1-height)/2
    y_min = 0.05+offset
    y_max = 0.05+feature_height-offset
    ys = (y_min, y_max, y_max, y_min)
    return xs, ys

# %% ../nbs/API/02_glyphs.ipynb 10
class Glyph:
    def __init__(self,
                 glyph_type: str ="arrow", # type of the Glyph (arrow or box)
                 colors: tuple = ("purple","orange"), # can be a single color or a tuple of two colors, one for each strand
                 alpha: float = 0.8, #transparency
                 show_name: bool = True, #
                 height: float = 1,  #height of the feature relative to other features (between 0 and 1)
                 ):
        """A class used to define the different types of glyphs shown for different feature types."""
        self.glyph_type=glyph_type
        if type(colors)==str:
            self.colors=(colors,)
        else:
            self.colors=colors

        assert alpha>=0 and alpha <=1
        self.alpha=alpha
        self.show_name=show_name
        assert height>0 and height<=1
        self.height=height

        if glyph_type == "box":
            self.coordinates = box_coordinates
        else:
            self.coordinates = arrow_coordinates

    def get_patch(self,
                  feature, # row of a pandas DataFrame extracted from a GFF file
                  feature_height: float = 0.15, #fraction of the annotation track height occupied by the features
                  ):
    
        if len(self.colors)>1:
            color_dic={"+":self.colors[0],
                    "-":self.colors[1]}
        else:
            color_dic=defaultdict(lambda: self.colors[0])

        return self.coordinates(feature, self.height, feature_height), color_dic[feature.strand], self.alpha
    
    def copy(self):
        return copy.deepcopy(self)
    
    def __repr__(self) -> str:
        attributes = ["glyph_type","colors","height","alpha","show_name"]
        r=f"Glyph object with attributes:\n"
        for attr in attributes:
            r+=f"\t{attr}: {getattr(self, attr)}\n"
        return r

# %% ../nbs/API/02_glyphs.ipynb 11
def get_default_glyphs() -> dict:
    """Returns a dictionnary with:

            * keys: feature types (str)
            * values: a Glyph object
    """
    basic_arrow=Glyph(glyph_type="arrow",colors=("purple","orange"),alpha=0.8,show_name=True)
    basic_box=Glyph(glyph_type="box",colors=("grey",),alpha=1,height=0.8,show_name=False)
    
    default_glyphs=defaultdict(lambda: basic_arrow.copy()) #the default glyph will be the same as for CDS etc.
    default_glyphs.update(dict([(f,basic_arrow.copy()) for f in ["CDS", "ncRNA", "rRNA", "tRNA"]]))
    default_glyphs['repeat_region']=basic_box.copy()
    default_glyphs['exon']=basic_box.copy()
    return default_glyphs

default_glyphs=get_default_glyphs()

# %% ../nbs/API/02_glyphs.ipynb 13
def get_patch_coordinates(feature, glyphs_dict, feature_height=0.15):
    glyph=glyphs_dict[feature.type]
    return glyph.get_patch(feature, feature_height=feature_height)

# %% ../nbs/API/02_glyphs.ipynb 15
def get_feature_name(feature,
                     glyphs_dict,
                     name="gene",
                     attributes: list = default_attributes,
                    ) -> str:
    """Gets the name of the feature to be displayed. If the Glyph for the feature type has the attribute show_name=False then an empty string is returned.
    If name is not an attribute of the feature, then the first attribute in the attributes list is used.
    """
    if glyphs_dict[feature.type].show_name:
        if hasattr(feature,name):
            if feature[name]:
                return feature[name]
        
        for attr in attributes:
            if feature[attr]:
                return feature[attr]
        
        return feature[9]
    else:
        return ""

# %% ../nbs/API/02_glyphs.ipynb 17
def get_feature_patches(features: pd.DataFrame, #DataFrame of the features 
                        left: int, #left limit
                        right: int, #right limit
                        glyphs_dict: dict, #a dictionnary of glyphs to use for each feature type
                        attributes: list = default_attributes, #list of attributes to display when hovering
                        name: str = default_attributes[0], #attribute to be displayed as the feature name
                        feature_height: float = 0.15, #fraction of the annotation track height occupied by the features
                       )->pd.DataFrame:
    features=features.loc[(features["right"] > left) & (features["left"] < right)]
    
    if len(features)>0:
        coordinates, colors, alphas = zip(*features.apply(get_patch_coordinates,glyphs_dict=glyphs_dict,feature_height=feature_height,axis=1))
        xs, ys = zip(*coordinates)
    else:
        colors = []
        xs, ys = [], []
        
    names=list(features.apply(get_feature_name,
                         name=name,
                         glyphs_dict=glyphs_dict,
                         axis=1))
        
    out=dict(names=list(names),
             xs=list(xs),
             ys=list(ys),
             color=list(colors),
             alpha=list(alphas),
             pos=list(features.middle.values),
            )
    for attr in attributes:
        if attr in features.columns:
            values=features[attr].fillna("").astype(str)
            out[attr]=values.to_list() #tried to split long strings here but Bokeh then ignores it 
            
    return pd.DataFrame(out)
