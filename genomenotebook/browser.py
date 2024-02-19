# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/API/00_browser.ipynb.

# %% auto 0
__all__ = ['GenomeBrowser', 'GenomeStack', 'GenomePlot']

# %% ../nbs/API/00_browser.ipynb 5
from fastcore.basics import *

from genomenotebook.utils import (
    parse_gff,
    parse_fasta,
    parse_genbank,
    add_z_order,
    in_wsl,
    add_extension,
    EmptyDataFrame,
)

from genomenotebook.glyphs import (
    get_feature_patches, 
    get_default_glyphs,
    _format_attribute
)

from genomenotebook.javascript import (
    x_range_change_callback_code,
    glyph_update_callback_code,
    search_callback_code,
    sequence_search_code,
    next_button_code,
    previous_button_code
)

from bokeh.models.tools import BoxZoomTool
from bokeh.models.glyphs import Patches

from bokeh.models import (
    CustomJS,
    Range1d,
    ColumnDataSource,
    AutocompleteInput,
    TextInput,
    Button,
    Rect,
    Div,
    Styles,
    TablerIcon,
    HoverTool, 
    NumeralTickFormatter, 
    LabelSet,
    HoverTool,
    TapTool,
    Quad
)

from bokeh.plotting import figure
from bokeh.plotting import show as bk_show #Need to rename the bokeh show function so that there is no confusion with GenomeBrowser.show
from bokeh.plotting import save as bk_save #Need to rename the bokeh show function so that there is no confusion with GenomeBrowser.show
from bokeh.plotting import output_file as bk_output_file #Need to rename the bokeh show function so that there is no confusion with GenomeBrowser.show
from bokeh.layouts import column, row

from Bio import SeqIO
import Bio

import numpy as np
import pandas as pd
import warnings
from typing import Union, List, Dict, Optional
from collections.abc import Mapping
from collections import defaultdict

# %% ../nbs/API/00_browser.ipynb 6
class GenomeBrowser:
    """Initialize a GenomeBrowser object.
    """
    _default_feature_types = ["CDS", "repeat_region", "ncRNA", "rRNA", "tRNA"]
    _default_attributes = ["gene", "locus_tag", "product"]
    
    def __init__(self,
                 gff_path: str = None, #path to the gff3 file of the annotations (also accepts gzip files)
                 genome_path: str = None, #path to the fasta file of the genome sequence
                 gb_path: str = None, #path to a genbank file
                 seq_id: str = None, #id of the sequence to load, for genomes with multiple contigs, defaults to the first sequence in the genbank or gff file.
                 init_pos: int = None, #initial position to display
                 init_win: int = 10000, #initial window size (max=20000)
                 bounds: tuple = None, #bounds can be specified. This helps preserve memory by not loading the whole genome if not needed.
                 max_interval: int = 100000, #maximum size of the field of view in bp
                 show_seq: bool = True, #creates a html div that shows the sequence when zooming in
                 search: bool = True, #enables a search bar
                 attributes: Union[list,Dict[str,Optional[list]]] = None , #list of attribute names from the GFF attributes column to be extracted. If dict then keys are feature types and values are lists of attributes. If None, then all attributes will be used.
                 feature_name: Union[str, dict] = "gene", #attribute to be displayed as the feature name. If str then use the same field for every feature type. If dict then keys are feature types and values are feature name attribute. feature_name is ignored if glyphs are provided.
                 feature_types: list = None, # list of feature types to display
                 glyphs: dict = None, #dictionnary defining the type and color of glyphs to display for each feature type
                 height: int = 150, # height of the annotation track
                 width: int = 600, # width of the inner frame of the browser
                 label_angle: int = 45, # angle of the feature names displayed on top of the features
                 label_font_size: str = "10pt", # font size fo the feature names
                 label_justify: str = "center", # center, left
                 label_vertical_offset: float = 0.03,
                 label_horizontal_offset = -5,
                 show_labels = True,
                 feature_height: float = 0.15, #fraction of the annotation track height occupied by the features
                 output_backend: str ="webgl", #can be "webgl" or "svg". webgl is more efficient but svg is a vectorial format that can be conveniently modified using other software
                 features:pd.DataFrame = None, # DataFrame with columns: ["seq_id", "source", "type", "start", "end", "score", "strand", "phase", "attributes"], where "attributes" is a dict of attributes.
                 seq:Bio.Seq.Seq = None, # keeps the Biopython sequence object
                 color_attribute = None, # feature attribute to be used as patch color
                 z_stack = False, #if true features that overlap will be stacked on top of each other
                 **kwargs, #additional keyword arguments are passed as is to bokeh.plotting.figure
                 ):
        
        
        ### Set attributes based on passed in values ###
        self.gff_path = gff_path
        self.genome_path = genome_path
        self.gb_path = gb_path
        self.seq_id = seq_id
        self.init_pos = init_pos
        self.init_win = init_win
        self.bounds = bounds
        self.max_interval = max_interval
        self.show_seq = show_seq
        self.search = search
        self.attributes = attributes
        self.feature_name = feature_name
        self.feature_types = feature_types
        self.glyphs = glyphs
        self.height = height
        self.width = width
        self.label_angle = label_angle
        self.label_font_size = label_font_size
        self.label_justify = label_justify
        self.label_vertical_offset = label_vertical_offset
        self.label_horizontal_offset = label_horizontal_offset
        self.show_labels = show_labels
        self.feature_height = feature_height
        self.output_backend = output_backend
        self.features = features
        self.seq = seq
        self.color_attribute = color_attribute
        self.z_stack = z_stack
        self.kwargs=kwargs
        
        
        ### assign defaults ###
        if feature_types is None:
            self.feature_types = self._default_feature_types.copy()

        if attributes is None:
            self.attributes    = self._default_attributes.copy()
        
        # If attribtues is a list then creates the self.attribtues dictionary with the same attributes list for each feature type
        if isinstance(self.attributes,List):
            self.attributes = {feature_type:self.attributes for feature_type in self.feature_types}

        # Aesthetics
        self.glyphs = get_default_glyphs() if glyphs==None else glyphs
        self.max_glyph_loading_range = 20000
        
        if glyphs==None: #if glyphs are provided then feature_name is ignored
            for feature_type in self.feature_types:
                if type(feature_name) is str:
                    self.glyphs[feature_type].name_attr = feature_name
                else:
                    feature_name_dic=defaultdict(lambda: "gene")
                    feature_name_dic.update(feature_name)
                    self.glyphs[feature_type].name_attr = feature_name_dic[feature_type]
        

        ### Load sequence and sequence annotations ###
        
        if sum(1 for x in [gff_path, gb_path, features] if x is not None) != 1:
            raise ValueError("Exactly one of gff_path, gb_path, or features must be provided")
        elif gff_path:
            self._get_gff_features()
        elif gb_path:
            self._get_genbank_features()
        else: # features supplied as a pandas dataframe
            if not self.seq_id:
                self.seq_id = self.features.loc[0,"seq_id"]
            

        
        if self.seq is None:
            self.seq_len = self.features.right.max()
        else:
            self.seq_len = len(self.seq)
        
        self.bounds = self.bounds if self.bounds != None else (0, self.seq_len)
        if self.seq is not None:
            self.seq=self.seq[self.bounds[0]:self.bounds[1]]

        

        ### initialize visualization ###
        if len(self.features)>0:
            if z_stack:
                add_z_order(self.features)
            self._prepare_data()
    
    def _get_gff_features(self):
        #if seq_id is not provided parse_gff will take the first contig in the file
        self.features = parse_gff(self.gff_path,
                        seq_id=self.seq_id,
                        bounds=self.bounds,
                        feature_types=self.feature_types,
                        attributes=self.attributes
                        )[0]
        self.seq_id = self.seq_id if self.seq_id else self.features.loc[0,"seq_id"]
        self._get_sequence_from_fasta()

    def _get_genbank_features(self):
        self.seq, self.features = parse_genbank(self.gb_path,
                        seq_id=self.seq_id,
                        bounds=self.bounds,
                        feature_types=self.feature_types,
                        attributes=self.attributes
                        )
        self.seq = self.seq[0]
        self.features = self.features[0]
        self.seq_id = self.seq_id if self.seq_id else self.features.loc[0,"seq_id"]
        
        

    
    def _get_sequence_from_fasta(self):
        """Looks for the sequence matching the seq_id and set bounds.
        """
        #if the sequence is provided then seq_len is the length of the reference sequence before bounds are applied
        #else seq_len is the right of the last feature
        if self.genome_path != None:
            try:
                self.seq = parse_fasta(self.genome_path, self.seq_id)
            except:
                warnings.warn(f"genome file {genome_path} cannot be parsed as a fasta file")
                self.show_seq = False #if a sequence is not provided or cannot be parsed then show_seq set to False
        else:
            self.show_seq = False #if a sequence is not provided or cannot be parsed then show_seq set to False


  
    def _prepare_data(self):
        self.patches = get_feature_patches(self.features, 
                                            self.bounds[0], 
                                            self.bounds[1],
                                            glyphs_dict=self.glyphs,
                                            attributes=self.attributes,
                                            feature_height = self.feature_height,
                                            label_vertical_offset =self.label_vertical_offset,
                                            label_justify=self.label_justify,
                                            color_attribute = self.color_attribute
                                            )
                                            

# %% ../nbs/API/00_browser.ipynb 7
class GenomeStack():
    def __init__(self, browsers = None):
        self.browsers = browsers
        if browsers is None:
            self.browsers = list()


    def show(self):
        for browser in self.browsers:
            browser._get_browser_elements()
        self.browsers[0].gene_track.xaxis.axis_label = self.browsers[0].seq_id
        if len(self.browsers) > 1:
            self.browsers[0].gene_track.xaxis.major_tick_line_color = None
            self.browsers[0].gene_track.xaxis.minor_tick_line_color = None
            self.browsers[0].gene_track.xaxis.major_label_text_font_size  = '0pt'
    
        for i, browser in enumerate(self.browsers[1:]):
            i = i+1
            track = self.browsers[0].add_track()
            track.fig = self.browsers[i].gene_track
            track.fig.axis.axis_label = self.browsers[i].seq_id
            track.fig.x_range = self.browsers[0].x_range
            if i < len(self.browsers)-1:
                track.fig.xaxis.major_tick_line_color = None
                track.fig.xaxis.minor_tick_line_color = None
                track.fig.xaxis.major_label_text_font_size  = '0pt'
    
        self.browsers[0].show()
        
        
    
    @classmethod
    def from_genbank(cls, 
                     genbank_path:str = None, # path to a genbank file
                     **kwargs # arguments to be passed to GenomeBrowser.__init__ for each browser being made
                    ):

        bounds = kwargs.get("bounds", None)        
        feature_types = kwargs.get("feature_types", GenomeBrowser._default_feature_types)
        feature_types = feature_types.copy()
        attributes = kwargs.get("attributes", GenomeBrowser._default_feature_types)
        attibutes = attributes.copy()

        if isinstance(attributes,List):
            attributes = {feature_type:attributes for feature_type in feature_types}
        
        seqs, features = parse_genbank(genbank_path,
                seq_id=None,
                first=False,
                bounds=bounds,
                feature_types=feature_types,
                attributes=attributes
                )
        out = list()
        for seq, feature in zip(seqs, features):
            out.append(GenomeBrowser(features=feature, seq=seq, **kwargs))
            
        
        return cls(out)
            
    

# %% ../nbs/API/00_browser.ipynb 8
class GenomePlot():
    def __init__(self, browser):
        self.browser = browser
        self.tracks=[]
        self.elements=[]
        
        self._get_gene_track()
        self.elements = self._collect_elements()
    
    def _get_gene_track(self):
        self._set_init_pos()
        if self.browser.init_win>self.browser.max_interval:
            warnings.warn("You requested an initial window larger than max_interval. Change max_interval to plot a larger window (this might overload your memory)")
        self.init_win = min(min(self.browser.init_win,self.browser.bounds[1]-self.browser.bounds[0]),self.browser.max_interval)

        semi_win = self.init_win / 2
            
        self.x_range = Range1d(
            max(self.browser.bounds[0],self.init_pos - semi_win), min(self.browser.bounds[1],self.init_pos + semi_win), 
            bounds=self.browser.bounds, 
            max_interval=self.browser.max_interval,
            min_interval=30
        )

        self.gene_track = figure(
            tools = "xwheel_zoom, xpan, save, reset",
            active_scroll = "xwheel_zoom",
            height = self.browser.height,
            x_range = self.x_range,
            y_range = Range1d(0, 1),
            output_backend=self.browser.output_backend,
            **self.browser.kwargs
        )
        # Add tool
        self.gene_track.add_tools(BoxZoomTool(dimensions="width"))

        # Format x axis values
        self.gene_track.xaxis[0].formatter = NumeralTickFormatter(format="0,0")
        # Hide grid
        self.gene_track.xgrid.visible = False
        self.gene_track.ygrid.visible = False
        # Hide axis
        self.gene_track.yaxis.visible = False

        self.gene_track.frame_width=self.browser.width
        self.x_range=self.gene_track.x_range
    
    def _set_init_pos(self):
        if self.browser.init_pos == None:
            self.init_pos=sum(self.browser.bounds)//2
        elif self.browser.init_pos>self.browser.bounds[1] or self.init_pos<self.browser.bounds[0]:
            warnings.warn("Requested an initial position outside of the browser bounds")
            self.init_pos=sum(self.browser.bounds)//2        

# %% ../nbs/API/00_browser.ipynb 16
@patch
def _add_annotations(self:GenomePlot):
    """
    Creates the Bokeh ColumnDataSource objects for the glyphs and add the glyphs and labels to the gene_track
    """
    
    #Filter initial glyphs by position
    feature_patches = self.browser.patches.loc[(
        self.browser.patches['xs'].apply(
            lambda x: max(x)>self.x_range.start-self.browser.max_glyph_loading_range)) & (
        self.browser.patches['xs'].apply(
            lambda x: min(x)<self.x_range.end+self.browser.max_glyph_loading_range)
        )].copy()
    
    self._glyph_source = ColumnDataSource(feature_patches.to_dict(orient="list"))
    
    #Information about the range currently plotted
    self._loaded_range = ColumnDataSource({"start":[self.x_range.start-self.browser.max_glyph_loading_range],
                                            "end":[self.x_range.end+self.browser.max_glyph_loading_range], 
                                            "range":[self.browser.max_glyph_loading_range]})
    
    glyph_renderer = self.gene_track.add_glyph(
        self._glyph_source, Patches(xs="xs", ys="ys", fill_color="color", fill_alpha="alpha")
    )
    # gene labels in the annotation track
    # This seems to be necessary to show the labels
    #self.gene_track.scatter(x="label_x", y=0, size=0, source=self._glyph_source)
    
    #ys = list()
    
    if self.browser.show_labels:
        labels = LabelSet(
            x="label_x",
            y="label_y",
            text="names",
            level="glyph",
            x_offset=self.browser.label_horizontal_offset,
            y_offset=0,
            source=self._glyph_source,
            text_align='left',
            text_font_size=self.browser.label_font_size,
            angle=self.browser.label_angle,
        )

        self.gene_track.add_layout(labels)
    self.gene_track.add_tools(
        HoverTool(
            renderers=[glyph_renderer],
            tooltips="<div>@attributes</div>",
        )
    )

# %% ../nbs/API/00_browser.ipynb 18
@patch
def _get_sequence_div(self:GenomePlot):
        ## Setting the div that will display the sequence
        sty=Styles(font_size='14px',
                font_family="Courrier",
                color="black",
                display="inline-block",
                overflow="hidden",
                background_color = "white",
                margin="0",
                margin_left= "2px",
                )
        
        self._div = Div(height=18, height_policy="fixed", 
                        width=self.browser.width, 
                        max_width=self.browser.width,
                        width_policy="fixed",
                        styles = sty,
                        )

# %% ../nbs/API/00_browser.ipynb 20
@patch
def _set_js_callbacks(self:GenomePlot):
        ## Adding the ability to display the sequence when zooming in
        self.sequence_dic = {
            'seq': str(self.browser.seq).upper() if self.browser.show_seq else "",
            'bounds':self.browser.bounds,
        }

        self._xcb = CustomJS(
            args={
                "x_range": self.gene_track.x_range,
                "sequence": self.sequence_dic,
                "all_glyphs":self.browser.patches.to_dict(orient="list"),
                "glyph_source": self._glyph_source,
                "div": self._div,
                "loaded_range":self._loaded_range,
            },
            code=x_range_change_callback_code
        )
        
        self._glyph_update_callback = CustomJS(
            args={
                "x_range": self.gene_track.x_range,
                "all_glyphs":self.browser.patches.to_dict(orient="list"),
                "glyph_source": self._glyph_source,
                "loaded_range":self._loaded_range,
            },
            code=glyph_update_callback_code
        )

        self.gene_track.x_range.js_on_change('start', self._xcb, self._glyph_update_callback)

# %% ../nbs/API/00_browser.ipynb 22
@patch
def _get_browser_elements(self:GenomePlot):
        self._add_annotations() 
        self._get_sequence_div()
        self._set_js_callbacks()

        if self.browser.show_seq:
            self.elements = [self.gene_track,self._div]
        else:
            self.elements = [self.gene_track]

# %% ../nbs/API/00_browser.ipynb 24
@patch
def _get_sequence_search(self:GenomePlot):
        seq_input = TextInput(placeholder="search by sequence")

        ## Adding BoxAnnotation to highlight search results
        search_span_source = ColumnDataSource({"x":[],"width":[],"fill_color":[]})#"y":[]
        h=Rect(x='x',y=0,
               width='width',
               height=self.gene_track.height,
               fill_color='fill_color',
               line_color="fill_color",
               fill_alpha=0.2,
               line_alpha=0.4)
        
        self.gene_track.add_glyph(search_span_source, h)

        call_back_sequence_search = CustomJS(
            args={
                "x_range": self.x_range,
                "sequence": self.sequence_dic,
                "bounds": self.browser.bounds,
                "search_span_source": search_span_source,
            },
            code=sequence_search_code
        )

        seq_input.js_on_change('value',call_back_sequence_search, self._xcb, self._glyph_update_callback)
        
        sty=Styles(
                   margin_left="1px",
                   margin_right="1px",
                   border = "none",
                   #width = "10px",
                )
        
        nextButton = Button(icon=TablerIcon("arrow-right"),
                            label="",
                            #button_type="primary",
                            styles = sty)
        
        nextButton_callback = CustomJS(
            args={
                "x_range": self.x_range,
                "bounds": self.browser.bounds,
                "search_span_source": search_span_source,
            },
            code=next_button_code)
        
        nextButton.js_on_event("button_click", nextButton_callback, self._xcb, self._glyph_update_callback)
        
        previousButton = Button(icon=TablerIcon("arrow-left"),
                                label="",
                                styles = sty,
                                #button_type="primary"
                               )
        
        previousButton_callback = CustomJS(
            args={
                "x_range": self.x_range,
                "bounds": self.browser.bounds,
                "search_span_source": search_span_source,
            },
            code=previous_button_code)
        
        previousButton.js_on_event("button_click", previousButton_callback, self._xcb, self._glyph_update_callback)

        return row(seq_input, previousButton, nextButton)

# %% ../nbs/API/00_browser.ipynb 26
@patch
def _get_search_box(self:GenomePlot):
        ## Create a text input widget for search
        completions=set()
        #for attr in self.patches.columns:
        #    if not attr in ["xs","ys","color","pos"]:
        #        completions.update(map(str,set(self.patches[attr])))
        completions.update(map(str,set(self.browser.patches["names"])))
        
        search_input = AutocompleteInput(completions=list(completions), placeholder="search by name")
        #search_input = TextInput()
        
        call_back_search = CustomJS(
            args={
                "x_range": self.x_range,
                "glyph_source": self._glyph_source,
                "bounds": self.browser.bounds,
                "all_glyphs": self.browser.patches.to_dict(orient="list"),
                "loaded_range": self._loaded_range,
                "div": self._div,
            },
            code=search_callback_code
        )

        search_input.js_on_change('value', call_back_search, self._xcb, self._glyph_update_callback)

        return search_input
    
    

# %% ../nbs/API/00_browser.ipynb 28
@patch
def _collect_elements(self:GenomePlot):
    self._get_browser_elements()
    elements = self.elements.copy()
    if self.browser.search:
        search_elements = [self._get_search_box()]
        if self.browser.show_seq:
             search_elements.append(self._get_sequence_search())
        elements = [row(search_elements)]+elements

    for track in self.tracks:
        elements.append(track.fig)
    return elements

# %% ../nbs/API/00_browser.ipynb 35
@patch
def show(self:GenomeBrowser):
    #bk_output_file("", "")
    plot = GenomePlot(self)
    
    bk_show(column(plot.elements))

# %% ../nbs/API/00_browser.ipynb 36
@patch
def save_html(self:GenomeBrowser, path:str, title:str=""):
    bk_output_file(path, title)
    elements = self.collect_elements()
    bk_save(column(elements), filename=path, title=title)

# %% ../nbs/API/00_browser.ipynb 54
from .track import Track

# %% ../nbs/API/00_browser.ipynb 55
@patch
def add_track(self: GenomePlot,
             height: int = 200, #size of the track
             tools: str = "xwheel_zoom, ywheel_zoom, pan, box_zoom, save, reset", #comma separated list of Bokeh tools that can be used to navigate the plot
             **kwargs,
             ) -> Track:
    """Adds a track to the GenomeBrowser. Ensures that the x_range are shared and figure widths are identical."""
    t = Track(height=height, 
              output_backend=self.output_backend,
              tools=tools,
              **kwargs)
    t.fig.x_range = self.x_range
    t.fig.frame_width = self.width
    t.bounds = self.bounds
    t.loaded_range = ColumnDataSource({"start":[self.x_range.start-self.browser.max_glyph_loading_range],
                                        "end":[self.x_range.end+self.browser.max_glyph_loading_range], 
                                        "range":[self.browser.max_glyph_loading_range]})
    t.max_glyph_loading_range = self.browser.max_glyph_loading_range
    self.tracks.append(t)
    return t
    

# %% ../nbs/API/00_browser.ipynb 58
@patch
def highlight(self:GenomeBrowser,
         data: pd.DataFrame, #pandas DataFrame containing the data
         left: str = "left", #name of the column containing the start positions of the regions
         right: str = "right", #name of the column containing the end positions of the regions
         color: str = "color", #color of the regions
         alpha: str = 0.2, #transparency
         hover_data: list = [], #list of additional column names to be shown when hovering over the data
         highlight_tracks: bool = False, #whether to highlight just the annotation track or also the other tracks
         **kwargs, #enables to pass keyword arguments used by the Bokeh function
        ):
    
    if type(hover_data)==str:
        hover_data = [hover_data]

    if color not in data.columns:
        data["color"]='green'

    data["alpha"]=alpha

    highlight_source = ColumnDataSource(data[[left,right,"color","alpha"]+hover_data])

    r=Quad(left=left, right=right,
           bottom=0,
           top=1,
           fill_color="color",
           fill_alpha="alpha",
           line_alpha=0,
           **kwargs)

    renderer= self.gene_track.add_glyph(highlight_source, r)
    tooltips=[(f"{left} - {right}",f"@{left} - @{right}")]+[(f"{attr}",f"@{attr}") for attr in hover_data]
    self.gene_track.add_tools(HoverTool(renderers=[renderer],
                                        tooltips=tooltips))
    
    if highlight_tracks:
        for t in self.tracks:
            t.highlight(data=data,left=left,right=right,color=color,alpha=alpha,hover_data=hover_data,**kwargs)

# %% ../nbs/API/00_browser.ipynb 62
from bokeh.io import export_svgs, export_svg, export_png
from selenium.webdriver.chrome.service import Service
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import os
from svgutils import compose
import chromedriver_binary

# %% ../nbs/API/00_browser.ipynb 63
@patch
def save(self:GenomeBrowser, 
         fname: str, #path to file or a simple name (extensions are automatically added)
        ):
        """This function saves the initial plot that is generated and not the current view of the browser.
        To save in svg format you must initialise your GenomeBrowser using `output_backend="svg"` """
        if len(self.features)>0:
            self._get_browser_elements()
            layout=column(self.elements + [t.fig for t in self.tracks])

        if in_wsl():
                ## Setup chrome options
                chrome_options = Options()
                chrome_options.add_argument("--headless") # Ensure GUI is off
                chrome_options.add_argument("--no-sandbox")
                chrome_options.add_argument("--disable-3d-apis")
                chrome_options.add_argument("--disable-blink-features")
                

                homedir = os.path.expanduser("~")
                try:
                        # webdriver_service = Service(f"{homedir}/chromedriver/stable/chromedriver")
                        # browser = webdriver.Chrome(service=webdriver_service, options=chrome_options)
                        browser = webdriver.Chrome(options=chrome_options)
                except:
                        warnings.warn("""If using WSL you can install chromedriver following these instructions:https://scottspence.com/posts/use-chrome-in-ubuntu-wsl
                                      Also make sure the chromedriver-binary python package has the same major version number as your chrome install.
                                      Check the chrome version using: google-chrome --version
                                       Then use pip to force install of a web driver with a compatible version, for example:
                                       pip install --force-reinstall -v "chromedriver-binary==121.0.6167.184.0"
                                       """)
                        browser=None

                
        else:
                browser=None

        base_name, ext = os.path.splitext(fname)
        if self.output_backend=="svg":
                fname=add_extension(fname,extension="svg")
                export_svgs(layout, filename=fname, webdriver=browser)
                if len(self.tracks)>0:
                    total_height=sum([self.height]+[t.height for t in self.tracks])
                    svgelements=[compose.SVG(fname)]
                    offset=self.height
                    for i,t in enumerate(self.tracks):
                        svgelements.append(
                            compose.SVG(f"{base_name}_{i+1}.svg").move(0,offset)
                        )
                        offset+=t.height
                        
                    compose.Figure(self.width+50, # +50 accounts for axis and labels
                                   total_height, 
                                   *svgelements).save(f"{base_name}_composite.svg")

        elif self.output_backend=="webgl":
                if ext.lower()==".svg":
                        warnings.warn('In order to save to svg you need to set the option output_backend="svg" when calling GenomeBrowser')

                fname=add_extension(fname,extension="png")
                export_png(layout, filename=fname, webdriver=browser)

# %% ../nbs/API/00_browser.ipynb 71
@patch
def add_tooltip_data(self:GenomeBrowser,
                    name: str, #name of the data to be added
                    values: str, #values 
                    feature_type: str = None, #specify the feature type if the data applies only a to specific feature_type  
                    ):

    flt=(self.patches.type == feature_type) | (feature_type is None)
    assert(len(self.patches.loc[flt])==len(values))
    for i,p in self.patches.loc[flt].iterrows():
        self.patches.loc[i,"attributes"] += "<br>"+_format_attribute(name,values[i])

