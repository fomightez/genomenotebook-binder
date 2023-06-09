# AUTOGENERATED! DO NOT EDIT! File to edit: ../nbs/API/00_browser.ipynb.

# %% auto 0
__all__ = ['GenomeBrowser']

# %% ../nbs/API/00_browser.ipynb 5
from fastcore.basics import *

from genomenotebook.utils import (
    parse_gff,
    in_wsl,
    add_extension,
)

from genomenotebook.glyphs import (
    get_feature_patches, 
    create_genome_browser_plot,
    get_default_glyphs,
)

from genomenotebook.javascript import (
    x_range_change_callback_code,
    glyph_update_callback_code,
    search_callback_code,
    sequence_search_code,
    next_button_code,
    previous_button_code
)
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
)
from bokeh.plotting import show
from bokeh.layouts import column, row

from Bio import SeqIO

import numpy as np
import warnings

# %% ../nbs/API/00_browser.ipynb 6
class GenomeBrowser:
    """Initialize a GenomeBrowser object.
    """
    def __init__(self,
                 gff_path: str, #path to the gff3 file of the annotations (also accepts gzip files)
                 genome_path: str = None, #path to the fasta file of the genome sequence
                 seq_id: str = None, #id of the sequence to show for genomes with multiple contigs
                 init_pos: int = None, #initial position to display
                 init_win: int = 10000, #initial window size (max=20000)
                 bounds: tuple = None, #bounds can be specified. This helps preserve memory by not loading the whole genome if not needed.
                 max_interval: int = 100000, #maximum size of the field of view in bp
                 show_seq: bool = True, #shows the sequence when zooming in
                 search: bool = True, #enables a search bar
                 attributes: list = ["gene", "locus_tag", "product"], #list of attribute names from the GFF attributes column to be extracted
                 feature_name: str = "gene", #attribute to be displayed as the feature name
                 feature_types: list = ["CDS", "repeat_region", "ncRNA", "rRNA", "tRNA"], # list of feature types to display
                 glyphs: dict = None, #dictionnary defining the type and color of glyphs to display for each feature type
                 height: int = 150, # height of the annotation track
                 width: int = 600, # width of the inner frame of the browser
                 label_angle: int = 45, # angle of the feature names displayed on top of the features
                 label_font_size: str = "10pt", # font size fo the feature names
                 feature_height: float = 0.15, #fraction of the annotation track height occupied by the features
                 output_backend: str ="webgl", #can be "webgl" or "svg". webgl is more efficient but svg is a vectorial format that can be conveniently modified using other software
                 **kwargs, #additional keyword arguments are passed as is to bokeh.plotting.figure
                 ):
        
        self.gff_path = gff_path
        self.genome_path = genome_path
        self.show_seq = show_seq if genome_path!=None else False
        self.attributes = attributes
        self.feature_types = feature_types
        self.feature_name = feature_name
        self.feature_height = feature_height
        self.glyphs = get_default_glyphs() if glyphs==None else glyphs

        self.features = parse_gff(gff_path,
                                      seq_id=seq_id,
                                      bounds=bounds,
                                      feature_types=feature_types
                                     )
        
        self.output_backend=output_backend
        self.kwargs=kwargs
        self.style_kwargs={}
        self.height=height
        for k in ["height","label_angle","label_font_size", "feature_height"]:
            self.style_kwargs[k]=locals()[k]
        
        
        self.bounds=bounds
        self.max_interval=max_interval
        self.search=search
        self.init_pos=init_pos
        self.init_win=init_win
        self.frame_width = width
        
        if len(self.features)>0:
            self._prepare_data()
            
    def _prepare_data(self):
        if self.feature_name not in self.features.columns:
            self.features[self.feature_name]=""

        self.seq_id = self.features.seq_id[0]
        self._get_sequence()

        if self.bounds == None: self.bounds=(0,self.seq_len)

        self.patches = get_feature_patches(self.features, 
                                         self.bounds[0], 
                                         self.bounds[1],
                                         glyphs_dict=self.glyphs,
                                         attributes=self.attributes,
                                         name = self.feature_name,
                                         feature_height = self.feature_height,
                                         )

        self._set_init_pos()
        self.init_win = min(self.init_win,self.bounds[1]-self.bounds[0])

        
        self.tracks=[]
        semi_win = self.init_win / 2
            
        self.x_range = Range1d(
            max(self.bounds[0],self.init_pos - semi_win), min(self.bounds[1],self.init_pos + semi_win), 
            bounds=self.bounds, 
            max_interval=self.max_interval,
            min_interval=30
        )

        self.max_glyph_loading_range = 20000
        self.highlight_regions = {"x":[],"width":[],"colors":[],"alpha":[]}

    def _get_sequence(self):
        if self.genome_path!=None: 
            rec_found=False
            for rec in SeqIO.parse(self.genome_path, 'fasta'):
                if rec.id==self.seq_id:
                    rec_found=True
                    break

            if not rec_found:
                warnings.warn("seq_id not found in fasta file")
            
            self.rec=rec
            self.seq_len = len(self.rec.seq) #length of the reference sequence before bounds are applied
            if self.bounds:
                self.rec.seq=self.rec.seq[self.bounds[0]:self.bounds[1]]    
        else: 
            self.seq_len = self.features.right.max()
        
    def _set_init_pos(self):
        if self.init_pos == None:
            self.init_pos=sum(self.bounds)//2
        elif self.init_pos>self.bounds[1] or self.init_pos<self.bounds[0]:
            warnings.warn("Requested an initial position outside of the browser bounds")
            self.init_pos=sum(self.bounds)//2


    def show(self):
        if len(self.features)>0:
            self.elements = self._get_browser(output_backend=self.output_backend,**self.style_kwargs,**self.kwargs)
            if self.search:
                search_elements = [self._get_search_box()]
                if self.show_seq:
                     search_elements.append(self._get_sequence_search())
                self.elements = [row(search_elements)]+self.elements
                #self.elements = [self._get_search_box()]+self.elements
            show(column(self.elements + [t.fig for t in self.tracks]))

    def _get_browser(self, **kwargs):
        
        #Filter initial glyphs by position
        feature_patches = self.patches.loc[(
            self.patches['xs'].apply(
                lambda x: max(x)>self.x_range.start-self.max_glyph_loading_range)) & (
            self.patches['xs'].apply(
                lambda x: min(x)<self.x_range.end+self.max_glyph_loading_range)
            )]
        
        self._glyph_source = ColumnDataSource(feature_patches.to_dict(orient="list"))
        
        #Information about the range currently plotted
        self._loaded_range = ColumnDataSource({"start":[self.x_range.start-self.max_glyph_loading_range],
                                                "end":[self.x_range.end+self.max_glyph_loading_range], 
                                                "range":[self.max_glyph_loading_range]})
        


        self.gene_track = create_genome_browser_plot(self._glyph_source, 
                                       self.x_range, 
                                       attributes=self.attributes,
                                       **kwargs)
        
        # Adding the possibility to highlight regions
        highlight_source = ColumnDataSource(self.highlight_regions)
        r=Rect(x='x',y=0,
               width='width',
               height=self.gene_track.height,
               fill_color="colors",
               fill_alpha="alpha",
               line_alpha=0)
        self.gene_track.add_glyph(highlight_source, r)
        
        self.gene_track.frame_width=self.frame_width

        ## Adding the ability to display the sequence when zooming in
        sequence = {
            'seq': str(self.rec.seq).upper() if self.show_seq else "",
            'bounds':self.bounds,
        }
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
                        width=self.frame_width, 
                        max_width=self.frame_width,
                        width_policy="fixed",
                        styles = sty,
                        )
        
        self._xcb = CustomJS(
            args={
                "x_range": self.gene_track.x_range,
                "sequence": sequence,
                "all_glyphs":self.patches.to_dict(orient="list"),
                "glyph_source": self._glyph_source,
                "div": self._div,
                "loaded_range":self._loaded_range,
            },
            code=x_range_change_callback_code
        )
        
        self._glyph_update_callback = CustomJS(
            args={
                "x_range": self.gene_track.x_range,
                "all_glyphs":self.patches.to_dict(orient="list"),
                "glyph_source": self._glyph_source,
                "loaded_range":self._loaded_range,
            },
            code=glyph_update_callback_code
        )

        self.gene_track.x_range.js_on_change('start', self._xcb, self._glyph_update_callback)
        self.x_range=self.gene_track.x_range

        if self.show_seq:
            return [self.gene_track,self._div]
        else:
            return [self.gene_track]
        
    def _get_sequence_search(self):
        seq_input = TextInput(placeholder="search by sequence")
        
        sequence = {
            'seq': str(self.rec.seq).upper() if self.show_seq else "",
            'bounds':self.bounds,
        }

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
                "sequence": sequence,
                "bounds": self.bounds,
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
                "bounds": self.bounds,
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
                "bounds": self.bounds,
                "search_span_source": search_span_source,
            },
            code=previous_button_code)
        
        previousButton.js_on_event("button_click", previousButton_callback, self._xcb, self._glyph_update_callback)

        return row(seq_input, previousButton, nextButton)
    
    def _get_search_box(self):
        ## Create a text input widget for search
        completions=set()
        #for attr in self.patches.columns:
        #    if not attr in ["xs","ys","color","pos"]:
        #        completions.update(map(str,set(self.patches[attr])))
        completions.update(map(str,set(self.patches["names"])))
        
        search_input = AutocompleteInput(completions=list(completions), placeholder="search by name")
        #search_input = TextInput()
        
        call_back_search = CustomJS(
            args={
                "x_range": self.x_range,
                "glyph_source": self._glyph_source,
                "bounds": self.bounds,
                "all_glyphs": self.patches.to_dict(orient="list"),
                "loaded_range": self._loaded_range,
                "div": self._div,
            },
            code=search_callback_code
        )

        search_input.js_on_change('value', call_back_search, self._xcb, self._glyph_update_callback)

        return search_input
    




# %% ../nbs/API/00_browser.ipynb 24
@patch
def highlight(self:GenomeBrowser,
              regions:list, #list of tuples with the format (start position, stop position)
              colors=None, #list of colors
              alpha=0.2, #transparency
             ):
    starts, stops = map(np.array,zip(*regions))
    width=stops-starts
    if not colors:
        colors=['green']*len(regions)
    alpha=[alpha]*len(regions)
    self.highlight_regions={"x":starts,"width":width,"colors":colors, "alpha":alpha}

# %% ../nbs/API/00_browser.ipynb 26
from .track import Track

# %% ../nbs/API/00_browser.ipynb 27
@patch
def add_track(self: GenomeBrowser,
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
    t.fig.frame_width = self.frame_width
    t.bounds = self.bounds
    t.loaded_range = ColumnDataSource({"start":[self.x_range.start-self.max_glyph_loading_range],
                                        "end":[self.x_range.end+self.max_glyph_loading_range], 
                                        "range":[self.max_glyph_loading_range]})
    t.max_glyph_loading_range = self.max_glyph_loading_range
    self.tracks.append(t)
    return t
    

# %% ../nbs/API/00_browser.ipynb 29
from bokeh.io import export_svgs, export_svg, export_png
from selenium.webdriver.chrome.service import Service
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import os
from svgutils import compose

# %% ../nbs/API/00_browser.ipynb 30
@patch
def save(self:GenomeBrowser, 
         fname: str, #path to file or a simple name (extensions are automatically added)
        ):
        """This function saves the initial plot that is generated and not the current view of the browser.
        To save in svg format you must initialise your GenomeBrowser using `output_backend="svg"` """
        if len(self.features)>0:
            self.elements = self._get_browser(output_backend=self.output_backend,**self.style_kwargs,**self.kwargs)
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
                        webdriver_service = Service(f"{homedir}/chromedriver/stable/chromedriver")
                        browser = webdriver.Chrome(service=webdriver_service, options=chrome_options)
                except:
                        warnings.warn("If using WSL you can install chromedriver following these instructions: https://cloudbytes.dev/snippets/run-selenium-and-chrome-on-wsl2 \n\
                                Keep the path to chromdriver as in these instructions: ~/chromedriver/stable/chromedriver")
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
                        
                    compose.Figure(self.frame_width+50, # +50 accounts for axis and labels
                                   total_height, 
                                   *svgelements).save(f"{base_name}_composite.svg")

        elif self.output_backend=="webgl":
                if ext.lower()==".svg":
                        warnings.warn('In order to save to svg you need to set the option output_backend="svg" when calling GenomeBrowser')

                fname=add_extension(fname,extension="png")
                export_png(layout, filename=fname, webdriver=browser)
