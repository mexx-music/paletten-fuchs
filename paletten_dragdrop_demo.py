
# CHANGELOG:
# - Refactored to class-based structure with PallettenFuchs main class
# - Added proper constants for trailer geometry and pallet dimensions
# - Implemented ceil-based grid calculations for accurate length measurements
# - Added three_rows_fixed() helper for consistent lane spacing
# - Added tail_close_clean_euro() for clean remainder handling
# - Implemented weight-aware industry/IBC placement with bias rules
# - Added axle balance estimation with front/back percentages
# - Improved mobile/iPad touch targets and responsive design
# - Added layout signature export for regression testing
# - Implemented Gewichtsmodus (weight mode) with balance-based sorting
# - Enhanced status display with detailed length and percentage info
# - Set Kühlsattel mode as default with fixed front buffer 20cm
# - Improved pallet placement for all variants with better remainder handling
# - Enhanced weight mode to work with any pallet count
# - Updated default display settings
# - Added Euro weight toggle (normal/heavy) for axle balance calculations
# - Added front-seeded placement patterns for weight optimization
# - Fixed Industry/IBC to place in side-by-side pairs per column
# - Enhanced Euro remainder rules to prevent single long pallets alone
# - Added deterministic recipes for 21/22/23/24 Euro patterns

from __future__ import annotations
import math
from dataclasses import dataclass
from typing import List, Tuple, Dict, Optional
import streamlit as st

# ---------- CONSTANTS ----------
TRAILER_L = 1360  # cm
TRAILER_W = 245   # cm
EURO_DEPTH_LONG = 120  # cm
EURO_WIDTH_LONG = 80   # cm
EURO_DEPTH_CROSS = 80  # cm
EURO_WIDTH_CROSS = 120 # cm
INDUSTRIE_DEPTH = 100  # cm
INDUSTRIE_WIDTH = 120  # cm
EURO_NORMAL_KG = 250   # kg
EURO_HEAVY_KG = 400    # kg
INDUSTRIE_LIGHT_WEIGHT = 600  # kg
INDUSTRIE_HEAVY_WEIGHT = 1100  # kg (IBC)

# Default UI settings
DEFAULT_CELL_CM = 40
DEFAULT_CELL_PX = 6
DEFAULT_AUTO_ZOOM = False

# Default Kühlsattel buffers
DEFAULT_FRONT_BUFFER = 20  # cm
DEFAULT_REAR_BUFFER = 0    # cm

@dataclass
class PalletType:
    """Represents a pallet type with dimensions and weight"""
    name: str
    depth_long: int     # cm, depth when placed longitudinally
    width_long: int     # cm, width when placed longitudinally  
    depth_cross: int    # cm, depth when placed crosswise
    width_cross: int    # cm, width when placed crosswise
    default_weight: int # kg

EURO = PalletType("Euro", EURO_DEPTH_LONG, EURO_WIDTH_LONG, EURO_DEPTH_CROSS, EURO_WIDTH_CROSS, EURO_NORMAL_KG)
INDUSTRIE = PalletType("Industrie", INDUSTRIE_DEPTH, INDUSTRIE_WIDTH, INDUSTRIE_DEPTH, INDUSTRIE_WIDTH, INDUSTRIE_LIGHT_WEIGHT)

class PallettenFuchs:
    """Main class for pallet optimization calculations and visualization"""
    
    def __init__(self, cell_cm: int = DEFAULT_CELL_CM, cell_px: int = DEFAULT_CELL_PX, 
                 auto_zoom: bool = DEFAULT_AUTO_ZOOM, front_buffer: int = DEFAULT_FRONT_BUFFER, 
                 rear_buffer: int = DEFAULT_REAR_BUFFER):
        self.cell_cm = cell_cm
        self.cell_px = cell_px
        self.auto_zoom = auto_zoom
        self.front_buffer = front_buffer
        self.rear_buffer = rear_buffer
        self.compute_grid()
    
    def compute_grid(self) -> None:
        """Compute grid dimensions using ceil-based calculations"""
        self.X = -(-TRAILER_L // self.cell_cm)  # Ceiling division
        self.Y = -(-TRAILER_W // self.cell_cm)  # Ceiling division
        
        if self.auto_zoom:
            self.cell_px = max(4, min(20, round(820 / self.X)))
        
        self.x_offset_cells = -(-self.front_buffer // self.cell_cm) if self.front_buffer > 0 else 0
        self.effective_length = max(0, TRAILER_L - self.front_buffer - self.rear_buffer)
        self.effective_x = max(0, self.X - self.x_offset_cells - (-(-self.rear_buffer // self.cell_cm)))
    
    def span_to_cells(self, depth_cm: int, width_cm: int) -> Tuple[int, int]:
        """Convert pallet dimensions to grid cells"""
        dx = -(-depth_cm // self.cell_cm)  # Ceiling division
        dy = -(-width_cm // self.cell_cm)  # Ceiling division
        return dx, dy
    
    def three_rows_fixed(self, dy: int) -> List[int]:
        """Get row positions that fit within trailer width"""
        if 3 * dy <= self.Y:
            # 3 rows fit with equalized gaps
            gap = (self.Y - 3 * dy) // 2
            return [0, gap + dy, gap + 2 * dy]
        elif 2 * dy <= self.Y:
            # Only 2 rows fit
            return [0, self.Y - dy]
        else:
            # Only 1 row fits (centered)
            return [max(0, (self.Y - dy) // 2)]
    
    def two_rows_fixed(self, dy: int) -> List[int]:
        """Get two row positions for cross items like Industry/IBC (120cm width)"""
        # For 245 cm trailer, if 2*dy <= Y, fits two rows; else one centered
        if 2 * dy <= self.Y:
            return [0, max(0, self.Y - dy)]
        return [max(0, (self.Y - dy) // 2)]
    
    def long_lanes(self) -> List[int]:
        """Get 3 evenly spaced lane starts based on long Euro dimensions"""
        dx_l, dy_l = self.span_to_cells(EURO_DEPTH_LONG, EURO_WIDTH_LONG)
        # Return 3 evenly spaced lane starts based on dy_l (not dy_cross!)
        total_gap = max(0, self.Y - 3 * dy_l)
        g = total_gap // 4
        r = total_gap % 4
        gaps = [g, g, g, g]
        for i in range(r):
            gaps[i] += 1
        y1 = gaps[0]
        y2 = y1 + dy_l + gaps[1]
        y3 = y2 + dy_l + gaps[2]
        return [y1, y2, min(y3, max(0, self.Y - dy_l))]
    
    def center_in_lane(self, lane_y: int, lane_h: int, item_h: int) -> int:
        """Center an item of height item_h within lane height lane_h starting at lane_y"""
        offset = max(0, (lane_h - item_h) // 2)
        return max(0, min(lane_y + offset, max(0, self.Y - item_h)))
    
    def empty_board(self) -> Tuple[List[List[bool]], List[Tuple], Dict[str, int]]:
        """Initialize empty board state"""
        occ = [[False] * self.X for _ in range(self.Y)]
        items = []  # (x, y, dx, dy, pallet_type, orientation, weight)
        placed = {"Euro": 0, "Industrie": 0, "IBC": 0}
        return occ, items, placed
    
    def is_free(self, occ: List[List[bool]], x: int, y: int, dx: int, dy: int) -> bool:
        """Check if area is free for placement"""
        if x < 0 or y < 0 or x + dx > self.X or y + dy > self.Y:
            return False
        for yy in range(y, y + dy):
            for xx in range(x, x + dx):
                if occ[yy][xx]:
                    return False
        return True
    
    def place_pallet(self, occ: List[List[bool]], items: List[Tuple], placed: Dict[str, int],
                    x: int, y: int, dx: int, dy: int, pallet_type: str, 
                    orientation: str, weight: int) -> None:
        """Place a pallet on the board"""
        for yy in range(y, y + dy):
            for xx in range(x, x + dx):
                occ[yy][xx] = True
        items.append((x, y, dx, dy, pallet_type, orientation, weight))
        placed[pallet_type] = placed.get(pallet_type, 0) + 1
    
    def place_euro_in_column(self, occ: List[List[bool]], items: List[Tuple], 
                            placed: Dict[str, int], x: int, count: int, orient: str, euro_kg: int) -> int:
        """Place 1-3 Euro pallets in a single column using proper lane spacing"""
        if orient == "long":
            dx, dy = self.span_to_cells(EURO_DEPTH_LONG, EURO_WIDTH_LONG)
            lanes = self.three_rows_fixed(dy)
        else:  # cross - align to long lanes
            dx, dy = self.span_to_cells(EURO_DEPTH_CROSS, EURO_WIDTH_CROSS)
            lanes_long = self.long_lanes()
            _, dy_l = self.span_to_cells(EURO_DEPTH_LONG, EURO_WIDTH_LONG)
            # Map to [top, mid, bottom] lane starts for CROSS centered inside long lane bands
            lanes = [
                self.center_in_lane(lanes_long[0], dy_l, dy),
                self.center_in_lane(lanes_long[1], dy_l, dy),
                self.center_in_lane(lanes_long[2], dy_l, dy),
            ]
        
        if x + dx > self.X:
            return 0
        
        placed_count = 0
        
        if count == 1:
            # Place in middle lane (index 1)
            if len(lanes) >= 2:
                y = lanes[1]  # Middle lane
                if self.is_free(occ, x, y, dx, dy):
                    self.place_pallet(occ, items, placed, x, y, dx, dy, "Euro", orient, euro_kg)
                    placed_count += 1
        elif count == 2:
            # Place in top and bottom (outer lanes)
            if len(lanes) >= 3:
                for y in [lanes[0], lanes[2]]:  # Top and bottom
                    if placed_count >= 2:
                        break
                    if self.is_free(occ, x, y, dx, dy):
                        self.place_pallet(occ, items, placed, x, y, dx, dy, "Euro", orient, euro_kg)
                        placed_count += 1
        elif count >= 3:
            # Place in all available lanes (up to 3)
            for y in lanes:
                if placed_count >= min(3, count):
                    break
                if self.is_free(occ, x, y, dx, dy):
                    self.place_pallet(occ, items, placed, x, y, dx, dy, "Euro", orient, euro_kg)
                    placed_count += 1
        
        return placed_count
    
    def fill_euro_full_columns(self, occ: List[List[bool]], items: List[Tuple], 
                              placed: Dict[str, int], x_start: int, euro_left: int, 
                              orient: str, euro_kg: int) -> Tuple[int, int]:
        """Fill complete 3-up columns of Euro pallets in specified orientation"""
        if orient == "long":
            dx, dy = self.span_to_cells(EURO_DEPTH_LONG, EURO_WIDTH_LONG)
        else:  # cross
            dx, dy = self.span_to_cells(EURO_DEPTH_CROSS, EURO_WIDTH_CROSS)
        
        x = x_start
        while euro_left >= 3 and x + dx <= self.X:
            placed_in_column = self.place_euro_in_column(occ, items, placed, x, 3, orient, euro_kg)
            if placed_in_column == 3:
                euro_left -= 3
                x += dx
            else:
                break
        
        return x, euro_left
    
    def tail_close_clean_euro(self, occ: List[List[bool]], items: List[Tuple], 
                             placed: Dict[str, int], x_start: int, euro_left: int, euro_kg: int) -> int:
        """Clean tail closure for remaining Euro pallets - prevents single long alone"""
        if euro_left <= 0:
            return 0
        
        dx_long, dy_long = self.span_to_cells(EURO_DEPTH_LONG, EURO_WIDTH_LONG)
        dx_cross, dy_cross = self.span_to_cells(EURO_DEPTH_CROSS, EURO_WIDTH_CROSS)
        
        # Try to place 3 in one column (prefer long)
        if euro_left >= 3:
            placed = self.place_euro_in_column(occ, items, placed, x_start, 3, "long", euro_kg)
            if placed == 3:
                return 3
            # Try cross if long failed
            placed = self.place_euro_in_column(occ, items, placed, x_start, 3, "cross", euro_kg)
            if placed > 0:
                return placed
        
        # Try to place 2 in one column (top+bottom, prefer long)
        if euro_left >= 2:
            placed = self.place_euro_in_column(occ, items, placed, x_start, 2, "long", euro_kg)
            if placed == 2:
                return 2
            # Try cross if long failed
            placed = self.place_euro_in_column(occ, items, placed, x_start, 2, "cross", euro_kg)
            if placed > 0:
                return placed
        
        # Place 1 in center (ALWAYS prefer cross centered in middle lane)
        if euro_left >= 1:
            # Always try cross-center first to prevent single long at front
            placed_count = self.place_euro_in_column(occ, items, placed, x_start, 1, "cross", euro_kg)
            if placed_count == 1:
                return 1
            # Try long middle only if cross doesn't fit
            placed_count = self.place_euro_in_column(occ, items, placed, x_start, 1, "long", euro_kg)
            if placed_count > 0:
                return placed_count
        
        return 0
    
    def block_industry_column_pairs(self, occ: List[List[bool]], items: List[Tuple], 
                                   placed: Dict[str, int], n_light: int, n_ibc: int) -> int:
        """Place industry/IBC pallets in side-by-side pairs per column, aligned to long outer lanes"""
        dx_i, dy_i = self.span_to_cells(INDUSTRIE_DEPTH, INDUSTRIE_WIDTH)  # cross footprint
        x = self.x_offset_cells
        
        # Align TOP/BOTTOM to outer LONG lanes
        lanes_long = self.long_lanes()
        _, dy_l = self.span_to_cells(EURO_DEPTH_LONG, EURO_WIDTH_LONG)
        top_y = self.center_in_lane(lanes_long[0], dy_l, dy_i)
        bot_y = self.center_in_lane(lanes_long[2], dy_l, dy_i)
        
        # Place light pallets first (prefer TOP, then BOTTOM)
        light_placed = 0
        while light_placed < n_light and x + dx_i <= self.X:
            placed_in_column = 0
            
            # Try TOP first, then BOTTOM
            for y in [top_y, bot_y]:
                if placed_in_column >= 2 or light_placed >= n_light:
                    break
                if self.is_free(occ, x, y, dx_i, dy_i):
                    self.place_pallet(occ, items, placed, x, y, dx_i, dy_i, "Industrie", "cross", INDUSTRIE_LIGHT_WEIGHT)
                    light_placed += 1
                    placed_in_column += 1
            
            # If odd item remains when starting fresh column, place at TOP
            if placed_in_column == 0 and light_placed < n_light:
                if self.is_free(occ, x, top_y, dx_i, dy_i):
                    self.place_pallet(occ, items, placed, x, top_y, dx_i, dy_i, "Industrie", "cross", INDUSTRIE_LIGHT_WEIGHT)
                    light_placed += 1
                    placed_in_column += 1
            
            if placed_in_column > 0:
                x += dx_i
            else:
                x += 1
        
        # Place IBC pallets (prefer BOTTOM, then TOP)
        ibc_placed = 0
        while ibc_placed < n_ibc and x + dx_i <= self.X:
            placed_in_column = 0
            
            # Try BOTTOM first, then TOP
            for y in [bot_y, top_y]:
                if placed_in_column >= 2 or ibc_placed >= n_ibc:
                    break
                if self.is_free(occ, x, y, dx_i, dy_i):
                    self.place_pallet(occ, items, placed, x, y, dx_i, dy_i, "IBC", "cross", INDUSTRIE_HEAVY_WEIGHT)
                    ibc_placed += 1
                    placed_in_column += 1
            
            # If odd item remains when starting fresh column, place at BOTTOM
            if placed_in_column == 0 and ibc_placed < n_ibc:
                if self.is_free(occ, x, bot_y, dx_i, dy_i):
                    self.place_pallet(occ, items, placed, x, bot_y, dx_i, dy_i, "IBC", "cross", INDUSTRIE_HEAVY_WEIGHT)
                    ibc_placed += 1
                    placed_in_column += 1
            
            if placed_in_column > 0:
                x += dx_i
            else:
                x += 1
        
        return x
    
    def generate_front_recipes(self, n_euro: int, n_light: int, n_ibc: int, euro_kg: int) -> List[Tuple]:
        """Generate deterministic recipes for specific Euro counts"""
        recipes = []
        remainder = n_euro % 3
        
        if remainder == 1:
            # Pattern: 1 cross in middle, then long columns
            occ, items, placed = self.empty_board()
            x = self.x_offset_cells
            
            # Place industry first
            if n_light > 0 or n_ibc > 0:
                x = self.block_industry_column_pairs(occ, items, placed, n_light, n_ibc)
            
            euro_left = n_euro
            # Seed with 1 cross centered in MIDDLE long lane
            if euro_left >= 1:
                placed_count = self.place_euro_in_column(occ, items, placed, x, 1, "cross", euro_kg)
                if placed_count > 0:
                    euro_left -= placed_count
                    dx_cross, _ = self.span_to_cells(EURO_DEPTH_CROSS, EURO_WIDTH_CROSS)
                    x += dx_cross
            
            # Fill long columns
            x, euro_left = self.fill_euro_full_columns(occ, items, placed, x, euro_left, "long", euro_kg)
            
            # Tail closure
            while euro_left > 0 and x < self.X:
                placed_count = self.tail_close_clean_euro(occ, items, placed, x, euro_left, euro_kg)
                if placed_count <= 0:
                    break
                euro_left -= placed_count
                dx_long, _ = self.span_to_cells(EURO_DEPTH_LONG, EURO_WIDTH_LONG)
                x += dx_long
            
            recipes.append((items, placed, "Recipe n%3=1"))
        
        if remainder == 2:
            # Pattern: 2 cross (top+bottom), then long columns
            occ, items, placed = self.empty_board()
            x = self.x_offset_cells
            
            # Place industry first
            if n_light > 0 or n_ibc > 0:
                x = self.block_industry_column_pairs(occ, items, placed, n_light, n_ibc)
            
            euro_left = n_euro
            # Seed with 2 cross TOP+BOTTOM (outer lanes)
            if euro_left >= 2:
                placed_count = self.place_euro_in_column(occ, items, placed, x, 2, "cross", euro_kg)
                if placed_count > 0:
                    euro_left -= placed_count
                    dx_cross, _ = self.span_to_cells(EURO_DEPTH_CROSS, EURO_WIDTH_CROSS)
                    x += dx_cross
            
            # Fill long columns
            x, euro_left = self.fill_euro_full_columns(occ, items, placed, x, euro_left, "long", euro_kg)
            
            # Tail closure
            while euro_left > 0 and x < self.X:
                placed_count = self.tail_close_clean_euro(occ, items, placed, x, euro_left, euro_kg)
                if placed_count <= 0:
                    break
                euro_left -= placed_count
                dx_long, _ = self.span_to_cells(EURO_DEPTH_LONG, EURO_WIDTH_LONG)
                x += dx_long
            
            recipes.append((items, placed, "Recipe n%3=2"))
        
        if remainder == 0 and n_euro > 0:
            # Pattern: All long 3-up columns
            occ, items, placed = self.empty_board()
            x = self.x_offset_cells
            
            # Place industry first
            if n_light > 0 or n_ibc > 0:
                x = self.block_industry_column_pairs(occ, items, placed, n_light, n_ibc)
            
            euro_left = n_euro
            # Fill all with long columns
            x, euro_left = self.fill_euro_full_columns(occ, items, placed, x, euro_left, "long", euro_kg)
            
            recipes.append((items, placed, "Recipe n%3=0"))
        
        return recipes
    
    def generate_euro_variant_cross_heavy(self, occ: List[List[bool]], items: List[Tuple], 
                                         placed: Dict[str, int], x_start: int, n_euro: int, euro_kg: int) -> None:
        """V1 - Cross-heavy variant: maximize cross columns, then tail close"""
        dx_cross, dy_cross = self.span_to_cells(EURO_DEPTH_CROSS, EURO_WIDTH_CROSS)
        x = x_start
        euro_left = n_euro
        
        # Fill maximum full cross columns (2 per column - top and bottom)
        while euro_left >= 2 and x + dx_cross <= self.X:
            placed_count = self.place_euro_in_column(occ, items, placed, x, 2, "cross", euro_kg)
            if placed_count > 0:
                euro_left -= placed_count
                x += dx_cross
            else:
                break
        
        # Handle remainder with improved tail close
        while euro_left > 0 and x < self.X:
            placed_count = self.tail_close_clean_euro(occ, items, placed, x, euro_left, euro_kg)
            if placed_count <= 0:
                break
            euro_left -= placed_count
            x += dx_cross  # Assume cross width for next attempt
    
    def generate_euro_variant_long_heavy(self, occ: List[List[bool]], items: List[Tuple], 
                                        placed: Dict[str, int], x_start: int, n_euro: int, euro_kg: int) -> None:
        """V2 - Long-heavy variant: maximize long columns, then tail close"""
        x = x_start
        euro_left = n_euro
        
        # Fill maximum full long columns (3 per column)
        x, euro_left = self.fill_euro_full_columns(occ, items, placed, x, euro_left, "long", euro_kg)
        
        # Handle remainder with improved tail close
        while euro_left > 0 and x < self.X:
            placed_count = self.tail_close_clean_euro(occ, items, placed, x, euro_left, euro_kg)
            if placed_count <= 0:
                break
            euro_left -= placed_count
            dx_long, _ = self.span_to_cells(EURO_DEPTH_LONG, EURO_WIDTH_LONG)
            x += dx_long
    
    def generate_euro_variant_only_long(self, occ: List[List[bool]], items: List[Tuple], 
                                       placed: Dict[str, int], x_start: int, n_euro: int, euro_kg: int) -> None:
        """V3 - Only long pallets in 3 lanes"""
        dx_long, dy_long = self.span_to_cells(EURO_DEPTH_LONG, EURO_WIDTH_LONG)
        x = x_start
        euro_left = n_euro
        
        while euro_left > 0 and x + dx_long <= self.X:
            placed_count = self.place_euro_in_column(occ, items, placed, x, min(3, euro_left), "long", euro_kg)
            if placed_count > 0:
                euro_left -= placed_count
                x += dx_long
            else:
                break
    
    def generate_euro_variant_mixed_lanes(self, occ: List[List[bool]], items: List[Tuple], 
                                         placed: Dict[str, int], x_start: int, n_euro: int, euro_kg: int) -> None:
        """V4 - Mixed lanes: prefer long per lane, allow cross if needed"""
        dx_long, dy_long = self.span_to_cells(EURO_DEPTH_LONG, EURO_WIDTH_LONG)
        dx_cross, dy_cross = self.span_to_cells(EURO_DEPTH_CROSS, EURO_WIDTH_CROSS)
        x = x_start
        euro_left = n_euro
        
        while euro_left > 0 and x < self.X:
            placed_in_column = 0
            
            # Try long placements first
            if x + dx_long <= self.X:
                placed_in_column = self.place_euro_in_column(occ, items, placed, x, min(3, euro_left), "long", euro_kg)
                if placed_in_column > 0:
                    euro_left -= placed_in_column
                    x += dx_long
                    continue
            
            # Try cross placements if long didn't work
            if x + dx_cross <= self.X:
                placed_in_column = self.place_euro_in_column(occ, items, placed, x, min(2, euro_left), "cross", euro_kg)
                if placed_in_column > 0:
                    euro_left -= placed_in_column
                    x += dx_cross
                    continue
            
            # If nothing could be placed, move to next column
            x += 1
    
    def generate_euro_variant_balanced(self, occ: List[List[bool]], items: List[Tuple], 
                                      placed: Dict[str, int], x_start: int, n_euro: int, euro_kg: int) -> None:
        """V5 - Balanced variant: alternate between long and cross for better weight distribution"""
        dx_long, dy_long = self.span_to_cells(EURO_DEPTH_LONG, EURO_WIDTH_LONG)
        dx_cross, dy_cross = self.span_to_cells(EURO_DEPTH_CROSS, EURO_WIDTH_CROSS)
        x = x_start
        euro_left = n_euro
        use_long = True  # Alternate between long and cross
        
        while euro_left > 0 and x < self.X:
            placed_in_column = 0
            
            if use_long and euro_left >= 2 and x + dx_long <= self.X:
                # Try long placement
                placed_in_column = self.place_euro_in_column(occ, items, placed, x, min(3, euro_left), "long", euro_kg)
                if placed_in_column > 0:
                    euro_left -= placed_in_column
                    x += dx_long
                    use_long = False  # Switch to cross next
                    continue
            
            if not use_long and euro_left >= 2 and x + dx_cross <= self.X:
                # Try cross placement
                placed_in_column = self.place_euro_in_column(occ, items, placed, x, min(2, euro_left), "cross", euro_kg)
                if placed_in_column > 0:
                    euro_left -= placed_in_column
                    x += dx_cross
                    use_long = True  # Switch to long next
                    continue
            
            # Fallback: try any placement
            if x + dx_long <= self.X:
                placed_in_column = self.place_euro_in_column(occ, items, placed, x, min(3, euro_left), "long", euro_kg)
                if placed_in_column > 0:
                    euro_left -= placed_in_column
                    x += dx_long
                    continue
            
            x += 1
    
    def generate_variants(self, n_euro: int, n_industrie_light: int, n_industrie_heavy: int, euro_kg: int) -> List[Tuple]:
        """Generate variants with the given pallet counts"""
        variants = []
        variant_names = ["Cross-heavy", "Long-heavy", "Only long", "Mixed lanes", "Balanced"]
        
        generators = [
            self.generate_euro_variant_cross_heavy,
            self.generate_euro_variant_long_heavy, 
            self.generate_euro_variant_only_long,
            self.generate_euro_variant_mixed_lanes,
            self.generate_euro_variant_balanced
        ]
        
        for i, generator in enumerate(generators):
            occ, items, placed = self.empty_board()
            x = self.x_offset_cells
            
            # Place industry pallets first using column pairs
            if n_industrie_light > 0 or n_industrie_heavy > 0:
                x = self.block_industry_column_pairs(occ, items, placed, n_industrie_light, n_industrie_heavy)
            
            # Place Euro pallets using the variant generator
            generator(occ, items, placed, x, n_euro, euro_kg)
            
            variants.append((items, placed, variant_names[i]))
        
        return variants
    
    def used_length_cm(self, items: List[Tuple]) -> int:
        """Calculate used length in cm deterministically"""
        if not items:
            return 0
        x_end_cells = max(x + dx for (x, y, dx, dy, pallet_type, orientation, weight) in items)
        return int(x_end_cells * self.cell_cm)
    
    def estimate_axle_balance(self, items: List[Tuple]) -> Tuple[int, int]:
        """Estimate axle balance as front/rear percentages"""
        if not items:
            return 50, 50
        
        total_weight = 0.0
        front_moment = 0.0
        
        for (x, y, dx, dy, pallet_type, orientation, weight) in items:
            x_cm_start = self.front_buffer + x * self.cell_cm
            x_cm_center = x_cm_start + (dx * self.cell_cm) / 2
            total_weight += weight
            
            # Simple position-based weighting (front = 1.0, rear = 0.0)
            effective_length = self.effective_length if self.effective_length > 0 else TRAILER_L
            pos_factor = max(0.0, 1.0 - (x_cm_center - self.front_buffer) / max(1.0, effective_length))
            front_moment += weight * pos_factor
        
        if total_weight <= 0:
            return 50, 50
        
        front_pct = int(round(100 * front_moment / total_weight))
        rear_pct = 100 - front_pct
        return front_pct, rear_pct
    
    def export_layout_signature(self, items: List[Tuple]) -> Dict:
        """Export layout signature for regression testing"""
        if not items:
            return {"total_items": 0, "used_length_cm": 0, "counts": {}}
        
        counts = {}
        min_x = min(x for (x, y, dx, dy, pallet_type, orientation, weight) in items)
        max_x = max(x + dx for (x, y, dx, dy, pallet_type, orientation, weight) in items)
        
        for (x, y, dx, dy, pallet_type, orientation, weight) in items:
            key = f"{pallet_type}_{orientation}"
            counts[key] = counts.get(key, 0) + 1
        
        return {
            "total_items": len(items),
            "used_length_cm": self.used_length_cm(items),
            "min_x": min_x,
            "max_x": max_x,
            "counts": counts,
            "cell_cm": self.cell_cm
        }
    
    def render_board_html(self, items: List[Tuple], flip_view: bool = False) -> str:
        """Generate HTML for board visualization"""
        html = f"""
        <div style='display:grid;
          grid-template-columns: repeat({self.X}, {self.cell_px}px);
          grid-auto-rows: {self.cell_px}px;
          gap: 1px;
          background:#ddd; padding:6px; border:2px solid #333; width:fit-content;'>
        """
        
        # Add buffer zone visualizations
        if flip_view:
            # Front buffer on RIGHT when flipped
            if self.x_offset_cells > 0:
                start_col = self.X - self.x_offset_cells + 1
                html += f"<div style='grid-column:{start_col}/span {self.x_offset_cells}; grid-row:1/span {self.Y}; background:#f3f3f3; border:1px dashed #999;'></div>"
            
            # Rear buffer on LEFT when flipped
            rear_buffer_cells = -(-self.rear_buffer // self.cell_cm) if self.rear_buffer > 0 else 0
            if rear_buffer_cells > 0:
                html += f"<div style='grid-column:1/span {rear_buffer_cells}; grid-row:1/span {self.Y}; background:#f3f3f3; border:1px dashed #999;'></div>"
        else:
            # Normal view - front buffer on LEFT
            if self.x_offset_cells > 0:
                html += f"<div style='grid-column:1/span {self.x_offset_cells}; grid-row:1/span {self.Y}; background:#f3f3f3; border:1px dashed #999;'></div>"
            
            # Rear buffer on RIGHT
            rear_buffer_cells = -(-self.rear_buffer // self.cell_cm) if self.rear_buffer > 0 else 0
            if rear_buffer_cells > 0:
                start_col = self.X - rear_buffer_cells + 1
                html += f"<div style='grid-column:{start_col}/span {rear_buffer_cells}; grid-row:1/span {self.Y}; background:#f3f3f3; border:1px dashed #999;'></div>"
        
        # Add pallet visualizations
        for (x, y, dx, dy, pallet_type, orientation, weight) in items:
            # Color coding: Euro long = light blue, Euro cross = light green, Industry/IBC = orange
            if pallet_type == "Euro":
                bg = "#e3f2fd" if orientation == "long" else "#e8f5e9"
            else:  # Industry or IBC
                bg = "#ffe0b2"
            
            if flip_view:
                # Flip x coordinate
                col_start = (self.X - (x + dx)) + 1
                html += f"<div style='grid-column:{col_start}/span {dx}; grid-row:{y+1}/span {dy}; background:{bg}; border:1px solid #777;'></div>"
            else:
                html += f"<div style='grid-column:{x+1}/span {dx}; grid-row:{y+1}/span {dy}; background:{bg}; border:1px solid #777;'></div>"
        
        html += "</div>"
        return html

# ---------- STREAMLIT APP ----------
st.set_page_config(page_title="🦊 Pal Fuchs – Varianten & Achslast", layout="wide")

# Add mobile-friendly CSS
st.markdown("""
<style>
    /* Improve touch targets for mobile/iPad */
    .stButton > button {
        min-height: 44px !important;
        padding: 12px 24px !important;
        font-size: 16px !important;
        touch-action: manipulation !important;
    }
    
    .stNumberInput > div > div > input {
        min-height: 44px !important;
        font-size: 16px !important;
        padding: 8px 12px !important;
    }
    
    .stSlider > div > div > div > div {
        min-height: 44px !important;
    }
    
    .stCheckbox > label {
        min-height: 44px !important;
        padding: 8px 0 !important;
        font-size: 16px !important;
    }
    
    /* Better spacing for mobile */
    .block-container {
        padding-top: 2rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
    }
    
    /* Prevent zoom on input focus for iOS */
    input, select, textarea {
        font-size: 16px !important;
    }
    
    /* Better column spacing on mobile */
    @media (max-width: 768px) {
        .stColumns > div {
            margin-bottom: 1rem !important;
        }
    }
</style>
""", unsafe_allow_html=True)

st.title("🦊 Pal Fuchs – Varianten & Gewichtsmodus")

# ---------- SIDEBAR CONFIGURATION ----------
with st.sidebar:
    st.markdown("### ⚙️ Anzeige")
    cell_cm = st.slider("Raster (cm/Zelle)", 20, 50, DEFAULT_CELL_CM, 5, key="cfg_cell_cm")
    auto_zoom = st.checkbox("Auto‑Zoom auf konstante Breite", DEFAULT_AUTO_ZOOM, key="cfg_auto_zoom")
    cell_px = st.slider("Zell‑Pixel", 4, 20, DEFAULT_CELL_PX, 1, disabled=auto_zoom, key="cfg_cell_px")
    
    st.markdown("---")
    st.markdown("### 🚛 Kühlsattel (Standard)")
    st.info(f"Front-Puffer: {DEFAULT_FRONT_BUFFER} cm\nHeck-Puffer: {DEFAULT_REAR_BUFFER} cm")
    
    st.markdown("---")
    st.markdown("### 📦 Euro Gewicht")
    euro_weight = st.radio("Euro weight", ["normal", "heavy"], index=0, horizontal=True)
    st.caption(f"Normal: {EURO_NORMAL_KG} kg, Heavy: {EURO_HEAVY_KG} kg")
    
    st.markdown("---")
    st.markdown("### ⚖️ Gewichtsmodus")
    weight_mode = st.checkbox("Gewichtsmodus aktivieren", False, key="cfg_weight_mode")
    st.caption("Sortiert Varianten nach optimaler Achslastverteilung")
    
    st.markdown("---")
    st.markdown("### 🔄 Ansicht")
    flip_view = st.checkbox("Ansicht spiegeln (Front rechts)", False, key="cfg_flip_view")
    st.caption("Spiegelt die Darstellung horizontal")

# Calculate Euro weight
euro_kg = EURO_HEAVY_KG if euro_weight == "heavy" else EURO_NORMAL_KG

# Initialize PallettenFuchs instance with fixed Kühlsattel buffers
fuchs = PallettenFuchs(
    cell_cm=cell_cm,
    cell_px=cell_px, 
    auto_zoom=auto_zoom,
    front_buffer=DEFAULT_FRONT_BUFFER,
    rear_buffer=DEFAULT_REAR_BUFFER
)

# ---------- MAIN INTERFACE ----------
st.markdown("### Eingaben")
c1, c2, c3, c4 = st.columns(4)
with c1:
    n_euro = st.number_input("Euro (120×80)", 0, 45, 33, key="n_euro")
with c2:
    n_industrie_light = st.number_input("Industrie leicht", 0, 30, 0, key="n_industrie_light")
with c3:
    n_industrie_heavy = st.number_input("IBC schwer", 0, 30, 0, key="n_industrie_heavy")
with c4:
    if st.button("Signatur ausgeben", key="export_signature"):
        st.session_state.show_signature = True

# Generate variants
variants = fuchs.generate_variants(int(n_euro), int(n_industrie_light), int(n_industrie_heavy), euro_kg)

# Add front recipes if weight mode is enabled
if weight_mode:
    front_recipes = fuchs.generate_front_recipes(int(n_euro), int(n_industrie_light), int(n_industrie_heavy), euro_kg)
    variants.extend(front_recipes)

# Apply weight mode sorting if enabled
if weight_mode and variants:
    # Sort by axle balance (closest to 50/50 first)
    def balance_score(variant_tuple):
        items, placed, name = variant_tuple
        front_pct, rear_pct = fuchs.estimate_axle_balance(items)
        return abs(front_pct - 50)  # Lower is better (closer to 50/50)
    
    variants.sort(key=balance_score)

# Variant navigation
if "variant_idx" not in st.session_state:
    st.session_state.variant_idx = 0

nvar = len(variants)
if nvar > 0:
    items, placed, variant_name = variants[st.session_state.variant_idx]
    
    # Display variant info
    mode_label = " (Gewichtsmodus)" if weight_mode else ""
    weight_label = f" [{euro_weight} Euro: {euro_kg}kg]"
    st.markdown(f"**Variante:** {st.session_state.variant_idx + 1} / {nvar} - {variant_name}{mode_label}{weight_label}")
    
    # Navigation buttons
    ncol1, ncol2 = st.columns(2)
    with ncol1:
        if st.button("◀ Vorherige Variante", key="variant_prev", use_container_width=True):
            st.session_state.variant_idx = (st.session_state.variant_idx - 1) % nvar
    with ncol2:
        if st.button("Nächste Variante ▶", key="variant_next", use_container_width=True):
            st.session_state.variant_idx = (st.session_state.variant_idx + 1) % nvar
    
    # Render board
    flip_view = st.session_state.get('cfg_flip_view', False)
    board_html = fuchs.render_board_html(items, flip_view)
    height_px = min(680, max(240, (fuchs.cell_px + 1) * fuchs.Y + 28))
    st.components.v1.html(board_html, height=height_px, scrolling=False)
    
    # Status information
    used_cm = fuchs.used_length_cm(items)
    share = used_cm / TRAILER_L if TRAILER_L else 0.0
    st.markdown(f"**Genutzte Länge:** {used_cm} cm von {TRAILER_L} cm (≈ {share:.0%})")
    
    front_pct, rear_pct = fuchs.estimate_axle_balance(items)
    st.markdown(f"**Achslast‑Schätzung:** vorne {front_pct}% / hinten {rear_pct}%")
    
    effective_length_display = fuchs.effective_length
    st.markdown(f"**Effektive Länge:** {effective_length_display} cm (mit Kühlsattel-Puffern)")
    
    # Show signature if requested
    if hasattr(st.session_state, 'show_signature') and st.session_state.show_signature:
        signature = fuchs.export_layout_signature(items)
        st.json(signature)
        st.session_state.show_signature = False

else:
    st.info("Keine gültigen Varianten mit den aktuellen Eingaben.")

# ---------- LEGEND ----------
with st.expander("🔎 Legende / Hinweise"):
    st.markdown(
        "- **Farbcode:** Euro längs = hellblau, Euro quer = hellgrün, Industrie/IBC = orange\n"
        "- Euro quer = 80×120 cm, Euro längs = 120×80 cm\n" 
        "- Industrie/IBC quer = 100×120 cm; schwere Güter (IBC) bevorzugt hinten\n"
        "- **Varianten:** Cross-heavy, Long-heavy, Only long, Mixed lanes, Balanced\n"
        "- **Gewichtsmodus:** Fügt deterministische Rezepte hinzu und sortiert nach Achslastverteilung\n"
        "- **Euro Gewicht:** Normal (250kg) vs Heavy (400kg) beeinflusst nur Achslastberechnung\n"
        f"- **Kühlsattel Standard:** Front {DEFAULT_FRONT_BUFFER} cm, Heck {DEFAULT_REAR_BUFFER} cm Puffer\n"
        "- **Industrie/IBC:** Immer als Paare pro Spalte platziert (oben+unten)\n"
        "- **Euro Remainder:** Verhindert einzelne Längspaletten; 1→Mitte, 2→oben+unten\n"
        "- Achslast‑Schätzung ist vereinfacht und dient zur Orientierung\n"
        "- **Ceil grid active:** Präzise Längenberechnung mit aufgerundeten Zellen\n"
        "- Graue gestrichelte Bereiche zeigen Pufferzonen (nicht nutzbar)"
    )
