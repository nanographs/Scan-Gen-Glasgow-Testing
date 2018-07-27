import logging
import struct
from enum import IntEnum
from migen import *


I2C_ADDR = 0b0010000


class RegEnum(IntEnum):
    def _generate_next_value_(name, start, count, last_values):
        return count


def _reg_fixed(frac):
    def conv(value):
        if isinstance(value, int):
            return value / (1 << frac)
        else:
            return int(value) * (1 << frac)
    return conv


regs = {
    # == 0x0000-0x0FFF Configuration Registers
    # - 0x0000-0x00FF Status Registers
    # 0x0000-0x000F General Status Registers
    "model_id":                             (0x0000, "H"),
    "revision_number":                      (0x0002, "B"),
    "manufacturer_id":                      (0x0003, "B"),
    "smia_version":                         (0x0004, "B"),
    "frame_count":                          (0x0005, "B"),
    "pixel_order":                          (0x0006, "B",
        RegEnum("PixelOrder", ("GRBG", "RGGB", "BGGR", "GBRG"))),
    "data_pedestal":                        (0x0008, "H"),
    "pixel_depth":                          (0x000C, "B"),
    # 0x0040-0x007F Frame Format Description
    "frame_format_model_type":              (0x0040, "B"),
    "frame_format_model_subtype":           (0x0041, "B"),
    "frame_format_descriptor":              (0x0042, "14H"),
    # 0x0080-0x0097 Analogue Gain Description Registers
    "analogue_gain_capability":             (0x0080, "H",
        RegEnum("AnalogueGainCapability", ("Global", "PerChannel"))),
    "analogue_gain_code_min":               (0x0084, "H"),
    "analogue_gain_code_max":               (0x0086, "H"),
    "analogue_gain_code_step":              (0x0088, "H"),
    "analogue_gain_code_type":              (0x008A, "H"),
    "analogue_gain_code_m0":                (0x008C, "H"),
    "analogue_gain_code_c0":                (0x008E, "H"),
    "analogue_gain_code_m1":                (0x0090, "H"),
    "analogue_gain_code_c1":                (0x0092, "H"),
    # 0x00C0-0x00FF Data Format Description
    "data_format_model_type":               (0x00C0, "B"),
    "data_format_model_subtype":            (0x00C1, "B"),
    "data_format_descriptor":               (0x00C2, "6H"),
    # - 0x0100-0x01FF Set-up Registers
    # 0x0100-0x010F General Set-up Registers
    "mode_select":                          (0x0100, "B"),
    "image_orientation":                    (0x0101, "B"),
    "software_reset":                       (0x0103, "B"),
    "grouped_parameter_hold":               (0x0104, "B"),
    "mask_corrupted_frames":                (0x0105, "B"),
    # 0x0110-0x011F Output Set-up Registers
    "ccp2_channel_identifier":              (0x0110, "B"),
    "ccp2_signalling_mode":                 (0x0111, "B",
        RegEnum("CCP2SignallingMode", ("Data_Clock", "Data_Strobe"))),
    "ccp_data_format":                      (0x0112, "H",
        RegEnum("CCPDataFormat", {
             "RAW6_Compressed": 0x0A06,
             "RAW7_Compressed": 0x0A07,
             "RAW8_Compressed": 0x0A08,
             "RAW8":  0x0808,
             "RAW10": 0x0A0A,
        })),
    # 0x0120-0x012F Integration Time and Gain Set-up Registers
    "gain_mode":                            (0x0120, "B",
        RegEnum("GainMode", ("Global", "PerChannel"))),
    # - 0x0200-0x02FF Integration Time and Gain Parameters
    # 0x2000-0x2003 Integration Time Registers
    "fine_integration_time":                (0x0200, "H"),
    "coarse_integration_time":              (0x0202, "H"),
    # 0x0204-0x020D Analogue Gain Registers
    "analogue_gain_code_global":            (0x0204, "H"),
    "analogue_gain_code_greenR":            (0x0206, "H"),
    "analogue_gain_code_red":               (0x0208, "H"),
    "analogue_gain_code_blue":              (0x020A, "H"),
    "analogue_gain_code_greenB":            (0x020C, "H"),
    "digital_gain_greenR":                  (0x020E, "H", _reg_fixed(8)),
    "digital_gain_red":                     (0x0210, "H", _reg_fixed(8)),
    "digital_gain_blue":                    (0x0212, "H", _reg_fixed(8)),
    "digital_gain_greenB":                  (0x0214, "H", _reg_fixed(8)),
    # - 0x0300-0x03FF Video Timing Registers
    # 0x0300-0x0307 Clock Set-up Registers
    "vt_pix_clk_div":                       (0x0300, "H"),
    "vt_sys_clk_div":                       (0x0302, "H"),
    "pre_pll_clk_div":                      (0x0304, "H"),
    "pll_multiplier":                       (0x0306, "H"),
    "op_pix_clk_div":                       (0x0308, "H"),
    "op_sys_clk_div":                       (0x030A, "H"),
    # 0x0340-0x0343 Frame Timing Registers
    "frame_length_lines":                   (0x0340, "H"),
    "line_length_pck":                      (0x0342, "H"),
    # 0x0344-0x034F Image Size Registers
    "x_addr_start":                         (0x0344, "H"),
    "y_addr_start":                         (0x0346, "H"),
    "x_addr_end":                           (0x0348, "H"),
    "y_addr_end":                           (0x034A, "H"),
    "x_output_size":                        (0x034C, "H"),
    "y_output_size":                        (0x034E, "H"),
    # 0x0380-0x0387 Sub-Sampling Registers
    "x_even_inc":                           (0x0380, "H"),
    "x_odd_inc":                            (0x0382, "H"),
    "y_even_inc":                           (0x0384, "H"),
    "y_odd_inc":                            (0x0386, "H"),
    # - 0x0400-0x04FF Image Scaling Registers
    "scaling_mode":                         (0x0400, "H",
        RegEnum("ScalingMode", ("None", "Horizontal", "Full"))),
    "spatial_sampling":                     (0x0402, "H",
        RegEnum("SpatialSampling", ("Bayer", "CoSited"))),
    "scale_m":                              (0x0404, "H"),
    "scale_n":                              (0x0406, "H"),
    # - 0x0500-0x05FF Image Compression Registers
    "compression_algorithm":                (0x0500, "H",
        RegEnum("CompressionCapability", ("None", "DPCM_PCM"))),
    # - 0x0600-0x06FF Test Pattern Registers
    "test_pattern_mode":                    (0x0600, "H",
        RegEnum("TestPatternMode", ("None", "SolidColour", "ColourBars", "FadeColourBars",
                                    "PN9"))),
    "test_data_red":                        (0x0602, "H"),
    "test_data_greenR":                     (0x0604, "H"),
    "test_data_blue":                       (0x0606, "H"),
    "test_data_greenB":                     (0x0608, "H"),
    "horizontal_cursor_width":              (0x060A, "H"),
    "horizontal_cursor_position":           (0x060C, "H"),
    "vertical_cursor_width":                (0x060E, "H"),
    "vertical_cursor_position":             (0x0610, "H"),
    # == 0x1000-0x1FFF Parameter Limit Registers
    # - 0x1000-0x10FF Integration Time and Gain Parameter Limit Registers
    # 0x1000-0x100B Integration Time Parameter Limit Registers
    "integration_time_capability":          (0x1000, "H",
        RegEnum("IntegrationTimeCapability", ("Coarse", "Coarse_Fine"))),
    "coarse_integration_time_min":          (0x1004, "H"),
    "coarse_integration_time_max_margin":   (0x1006, "H"),
    "fine_integration_time_min":            (0x1008, "H"),
    "fine_integration_time_max_margin":     (0x100A, "H"),
    # 0x1080-0x1089 Digital Gain Parameter Limit Registers
    "digital_gain_capability":              (0x1080, "H",
        RegEnum("DigitalGainCapability", ("None", "PerChannel"))),
    "digital_gain_min":                     (0x1084, "H", _reg_fixed(8)),
    "digital_gain_max":                     (0x1086, "H", _reg_fixed(8)),
    "digital_gain_step_size":               (0x1088, "H", _reg_fixed(8)),
    # - 0x1100-0x11FF Video Timing Parameter Limit Registers
    # 0x1100-0x111F Pre-PLL and PLL Clock Set-up Capability Registers
    "min_ext_clk_freq_mhz":                 (0x1100, "f"),
    "max_ext_clk_freq_mhz":                 (0x1104, "f"),
    "min_pre_pll_clk_div":                  (0x1108, "H"),
    "max_pre_pll_clk_div":                  (0x110A, "H"),
    "min_pll_ip_freq_mhz":                  (0x110C, "f"),
    "max_pll_ip_freq_mhz":                  (0x1110, "f"),
    "min_pll_multiplier":                   (0x1114, "H"),
    "max_pll_multiplier":                   (0x1116, "H"),
    "min_pll_op_freq_mhz":                  (0x1118, "f"),
    "max_pll_op_freq_mhz":                  (0x111C, "f"),
    # 0x1120-0x1137 Video Timing Clock Set-up Capability Registers
    "min_vt_sys_clk_div":                   (0x1120, "H"),
    "max_vt_sys_clk_div":                   (0x1122, "H"),
    "min_vt_sys_clk_freq_mhz":              (0x1124, "f"),
    "max_vt_sys_clk_freq_mhz":              (0x1128, "f"),
    "min_vt_pix_clk_freq_mhz":              (0x112C, "f"),
    "max_vt_pix_clk_freq_mhz":              (0x1130, "f"),
    "min_vt_pix_clk_div":                   (0x1134, "H"),
    "max_vt_pix_clk_div":                   (0x1136, "H"),
    # 0x1140-0x1149 Frame Timing Parameter Limit Registers
    "min_frame_length_lines":               (0x1140, "H"),
    "max_frame_length_lines":               (0x1142, "H"),
    "min_line_length_pck":                  (0x1144, "H"),
    "max_line_length_pck":                  (0x1146, "H"),
    "min_line_blanking_pck":                (0x1148, "H"),
    # 0x1160-0x1177 Output Clock Set-up Capability Registers
    "min_op_sys_clk_div":                   (0x1160, "H"),
    "max_op_sys_clk_div":                   (0x1162, "H"),
    "min_op_sys_clk_freq_mhz":              (0x1164, "f"),
    "max_op_sys_clk_freq_mhz":              (0x1168, "f"),
    "min_op_pix_clk_div":                   (0x116C, "H"),
    "max_op_pix_clk_div":                   (0x116E, "H"),
    "min_op_pix_clk_freq_mhz":              (0x1170, "f"),
    "max_op_pix_clk_freq_mhz":              (0x1174, "f"),
    # 0x1180-0x1187 Image Size Parameter Limit Registers
    "x_addr_min":                           (0x1180, "H"),
    "y_addr_min":                           (0x1182, "H"),
    "x_addr_max":                           (0x1184, "H"),
    "y_addr_max":                           (0x1186, "H"),
    # 0x11C0-0x011C7 Sub-Sampling Parameter Limit Registers
    "min_even_inc":                         (0x11C0, "H"),
    "max_even_inc":                         (0x11C2, "H"),
    "min_odd_inc":                          (0x11C4, "H"),
    "max_odd_inc":                          (0x11C8, "H"),
    # - 0x1200-0x12FF Image Scaling Parameter Limit Registers
    "scaling_capability":                   (0x1200, "H",
        RegEnum("ScalingCapability", ("None", "Horizontal", "Full"))),
    "scaler_m_min":                         (0x1204, "H"),
    "scaler_m_max":                         (0x1206, "H"),
    "scaler_n_min":                         (0x1208, "H"),
    "scaler_n_max":                         (0x120A, "H"),
    # - 0x1300-0x13FF Image Compression Capability Registers
    "compression_capability":               (0x1300, "H",
        RegEnum("CompressionCapability", ("None", "DPCM_PCM"))),
    # - 0x1400-0x14FF Colour Matrix Registers
    "matrix_element_RedInRed":              (0x1400, "2b"),
    "matrix_element_GreenInRed":            (0x1402, "2b"),
    "matrix_element_BlueInRed":             (0x1404, "2b"),
    "matrix_element_RedInGreen":            (0x1406, "2b"),
    "matrix_element_GreenInGreen":          (0x1408, "2b"),
    "matrix_element_BlueInGreen":           (0x140A, "2b"),
    "matrix_element_RedInBlue":             (0x140C, "2b"),
    "matrix_element_GreenInBlue":           (0x140E, "2b"),
    "matrix_element_BlueInBlue":            (0x1410, "2b"),
    # == 0x2000-0x2FFF Image Statistics Registers
    # == 0x3000-0x3FFF Manufacturer Specific Registers
}


class SMIACCIError(Exception):
    pass


class SMIACCIInterface:
    def __init__(self, interface, logger):
        self.lower     = interface
        self._logger   = logger
        self._level    = logging.DEBUG if self._logger.name == __name__ else logging.TRACE

    def read(self, addr, size):
        msb = (addr >> 8) & 0xff
        lsb = (addr >> 0) & 0xff
        result = self.lower.write(I2C_ADDR, [msb, lsb])
        if result:
            result = self.lower.read(I2C_ADDR, size)
        if result in (False, None):
            raise SMIACCIError("MIPI CCI: addr={:#04x} read not acked".format(addr))

        return result

    def write(self, addr, data):
        msb = (addr >> 8) & 0xff
        lsb = (addr >> 0) & 0xff
        result = self.lower.write(I2C_ADDR, [msb, lsb, *data])
        if result is None:
            raise SMIACCIError("MIPI CCI: addr={:#04x} write not acked".format(addr))


class interval:
    def __init__(self, lower, upper=None, step=None):
        self.lower = lower
        self.upper = upper
        self.step  = step

    def __contains__(self, value):
        if self.lower is None:
            return value <= self.upper
        elif self.upper is None:
            return value >= self.lower

        if not self.lower <= value <= self.upper:
            return False
        if self.step is not None and (value - self.lower) % self.step != 0:
            return False
        return True

    def __iter__(self):
        value = self.lower
        while value <= self.upper:
            yield value
            if isinstance(value, int) and self.step is None:
                value += 1
            else:
                value += step

    def __reversed__(self):
        value = self.upper
        while value >= self.lower:
            yield value
            if isinstance(value, int) and self.step is None:
                value -= 1
            else:
                value -= step

    def __str__(self):
        if isinstance(self.lower, float):
            formatter = lambda x: "%.2f" % x
        elif isinstance(self.lower, int):
            formatter = lambda x: "%d" % x

        fmt_lower = "(-inf  " if self.lower is None else "[" + "%6s" % formatter(self.lower)
        fmt_upper = "   inf)" if self.upper is None else "%6s" % formatter(self.upper) + "]"
        fmt_step  =      None if self.step  is None else formatter(self.step)
        if fmt_step:
            return "%s, %s (step %s)" % (fmt_lower, fmt_upper, fmt_step)
        else:
            return "%s, %s" % (fmt_lower, fmt_upper)


def _memoize(getter):
    field_name = "_cached_{}".format(getter.__name__)
    def memoized_getter(self):
        if hasattr(self, field_name):
            return getattr(self, field_name)
        else:
            value = getter(self)
            setattr(self, field_name, value)
            return value
    return memoized_getter


class SMIACamera:
    def __init__(self, interface, logger, extclk_freq):
        self._iface  = interface
        self._logger = logger
        self._level  = logging.DEBUG if self._logger.name == __name__ else logging.TRACE
        self._ext_clk_freq_mhz = extclk_freq / 1e6

    def get(self, reg):
        addr, fmt, *conv = regs[reg]
        value, = struct.unpack(">" + fmt, self._iface.read(addr, struct.calcsize(fmt)))
        if conv:
            value = conv[0](value)
        self._logger.log(self._level, "MIPI CCI: reg=%s(%#06x) get=%s",
                         reg, addr, value)
        return value

    def set(self, reg, value):
        addr, fmt, *conv = regs[reg]
        if conv:
            value = conv[0][value]
        self._logger.log(self._level, "MIPI CCI: reg=%s(%#06x) set=%s",
                         reg, addr, value)
        self._iface.write(addr, struct.pack(">" + fmt, value))

    def _show(self, name, fmt, *args):
        self._logger.info(" %-36s " + fmt, name, *args)

    # CAMERA INFO

    @_memoize
    def get_model_id(self):
        return self.get("model_id")

    @_memoize
    def get_revision_number(self):
        return self.get("revision_number")

    @_memoize
    def get_manufacturer_id(self):
        return self.get("manufacturer_id")

    @_memoize
    def get_smia_version(self):
        version = self.get("smia_version")
        return (version / 10, version % 10)

    def show_info(self):
        self._logger.info("CAMERA INFO:")
        self._logger.info(" camera IDs: model %#06x revision %#02x mfgr %#04x",
            self.get_model_id(), self.get_revision_number(), self.get_manufacturer_id())
        self._logger.info(" SMIA version %d.%d",
            *self.get_smia_version())

    # CAMERA LIMITS

    @_memoize
    def get_ext_clk_freq_mhz_range(self):
        return interval(self.get("min_ext_clk_freq_mhz"),
                        self.get("max_ext_clk_freq_mhz"))

    @_memoize
    def get_pre_pll_clk_div_range(self):
        return interval(self.get("min_pre_pll_clk_div"),
                        self.get("max_pre_pll_clk_div"))

    @_memoize
    def get_pll_input_freq_mhz_range(self):
        return interval(self.get("min_pll_ip_freq_mhz"),
                        self.get("max_pll_ip_freq_mhz"))

    @_memoize
    def get_pll_multiplier_range(self):
        return interval(self.get("min_pll_multiplier"),
                        self.get("max_pll_multiplier"))

    @_memoize
    def get_pll_output_freq_mhz_range(self):
        return interval(self.get("min_pll_op_freq_mhz"),
                        self.get("max_pll_op_freq_mhz"))

    @_memoize
    def get_vt_sys_clk_div_range(self):
        return interval(self.get("min_vt_sys_clk_div"),
                        self.get("max_vt_sys_clk_div"))

    @_memoize
    def get_vt_sys_clk_freq_mhz_range(self):
        return interval(self.get("min_vt_sys_clk_freq_mhz"),
                        self.get("max_vt_sys_clk_freq_mhz"))

    @_memoize
    def get_vt_pix_clk_div_range(self):
        return interval(self.get("min_vt_pix_clk_div"),
                        self.get("max_vt_pix_clk_div"))

    @_memoize
    def get_vt_pix_clk_freq_mhz_range(self):
        return interval(self.get("min_vt_pix_clk_freq_mhz"),
                        self.get("max_vt_pix_clk_freq_mhz"))

    @_memoize
    def get_op_sys_clk_div_range(self):
        return interval(self.get("min_op_sys_clk_div"),
                        self.get("max_op_sys_clk_div"))

    @_memoize
    def get_op_sys_clk_freq_mhz_range(self):
        return interval(self.get("min_op_sys_clk_freq_mhz"),
                        self.get("max_op_sys_clk_freq_mhz"))

    @_memoize
    def get_op_pix_clk_div_range(self):
        return interval(self.get("min_op_pix_clk_div"),
                        self.get("max_op_pix_clk_div"))

    @_memoize
    def get_op_pix_clk_freq_mhz_range(self):
        return interval(self.get("min_op_pix_clk_freq_mhz"),
                        self.get("max_op_pix_clk_freq_mhz"))

    @_memoize
    def get_integration_time_capability(self):
        return self.get("integration_time_capability")

    @_memoize
    def get_coarse_integration_time_range(self):
        return interval(self.get("coarse_integration_time_min"),
                        self.get("coarse_integration_time_max_margin"))

    @_memoize
    def get_fine_integration_time_range(self):
        return interval(self.get("fine_integration_time_min"),
                        self.get("fine_integration_time_max_margin"))

    @_memoize
    def get_analogue_gain_capability(self):
        return self.get("analogue_gain_capability")

    @_memoize
    def get_analogue_gain_range(self):
        return interval(self.get("analogue_gain_code_min"),
                        self.get("analogue_gain_code_max"),
                        self.get("analogue_gain_code_step"))

    @_memoize
    def get_digital_gain_capability(self):
        return self.get("digital_gain_capability")

    @_memoize
    def get_digital_gain_range(self):
        return interval(self.get("digital_gain_min"),
                        self.get("digital_gain_max"),
                        self.get("digital_gain_step_size"))

    @_memoize
    def get_frame_length_lines_range(self):
        return interval(self.get("min_frame_length_lines"),
                        self.get("max_frame_length_lines"))

    @_memoize
    def get_line_length_pck_range(self):
        return interval(self.get("min_line_length_pck"),
                        self.get("max_line_length_pck"))

    @_memoize
    def get_line_blanking_pck_range(self):
        return interval(self.get("min_line_blanking_pck"))

    @_memoize
    def get_x_addr_range(self):
        return interval(self.get("x_addr_min"),
                        self.get("x_addr_max"))

    @_memoize
    def get_y_addr_range(self):
        return interval(self.get("y_addr_min"),
                        self.get("y_addr_max"))

    @_memoize
    def get_even_inc_range(self):
        return interval(self.get("min_even_inc"),
                        self.get("max_even_inc"))

    @_memoize
    def get_odd_inc_range(self):
        return interval(self.get("min_odd_inc"),
                        self.get("max_odd_inc"))

    @_memoize
    def get_scaling_capability(self):
        return self.get("scaling_capability")

    @_memoize
    def get_scaler_m_range(self):
        return interval(self.get("scaler_m_min"),
                        self.get("scaler_m_max"))

    @_memoize
    def get_scaler_n_range(self):
        return interval(self.get("scaler_n_min"),
                        self.get("scaler_n_max"))

    @_memoize
    def get_compression_capability(self):
        return self.get("compression_capability")

    def show_limits(self):
        self._logger.info("CAMERA LIMITS:")
        self._show("external clock frequency limits", "%s MHz",
            self.get_ext_clk_freq_mhz_range())
        self._show("pre-PLL divider limits", "%s",
            self.get_pre_pll_clk_div_range())
        self._show("PLL input frequency limits", "%s MHz",
            self.get_pll_input_freq_mhz_range())
        self._show("PLL multiplier limits", "%s",
            self.get_pll_multiplier_range())
        self._show("PLL output frequency limits", "%s MHz",
            self.get_pll_output_freq_mhz_range())
        self._show("video system clock divider limits", "%s",
            self.get_vt_sys_clk_div_range())
        self._show("video system clock frequency limits", "%s MHz",
            self.get_vt_sys_clk_freq_mhz_range())
        self._show("video pixel clock divider limits", "%s",
            self.get_vt_pix_clk_div_range())
        self._show("video pixel clock frequency limits", "%s MHz",
            self.get_vt_pix_clk_freq_mhz_range())
        self._show("output system clock divider limits", "%s",
            self.get_op_sys_clk_div_range())
        self._show("output system clock frequency limits", "%s MHz",
            self.get_op_sys_clk_freq_mhz_range())
        self._show("output pixel clock divider limits", "%s",
            self.get_op_pix_clk_div_range())
        self._show("output pixel clock frequency limits", "%s MHz",
            self.get_op_pix_clk_freq_mhz_range())
        self._show("integration time capability", "%s",
            self.get_integration_time_capability().name)
        self._show("coarse integration time limits", "%s lines",
            self.get_coarse_integration_time_range())
        self._show("fine integration time limits", "%s pixels",
            self.get_fine_integration_time_range())
        self._show("analogue gain capability", "%s",
            self.get_analogue_gain_capability().name)
        self._show("analogue gain code limits", "%s",
            self.get_analogue_gain_range())
        self._show("digital gain capability", "%s",
            self.get_digital_gain_capability().name)
        self._show("digital gain limits", "%s",
            self.get_digital_gain_range())
        self._show("frame length limits", "%s lines",
            self.get_frame_length_lines_range())
        self._show("line length limits", "%s pixel clocks",
            self.get_line_length_pck_range())
        self._show("line blanking limit", "%s pixel clocks",
            self.get_line_blanking_pck_range())
        self._show("pixel array X-address limits", "%s",
            self.get_x_addr_range())
        self._show("pixel array Y-address limits", "%s",
            self.get_y_addr_range())
        self._show("even pixels increment limits", "%s",
            self.get_even_inc_range())
        self._show("odd pixels increment limits", "%s",
            self.get_odd_inc_range())
        self._show("scaling capability", "%s",
            self.get_scaling_capability().name)
        self._show("scaler M parameter limits", "%s",
            self.get_scaler_m_range())
        self._show("scaler N parameter limits", "%s",
            self.get_scaler_n_range())
        self._show("compression capability", "%s",
           self.get_compression_capability().name)

    # CAMERA CLOCKING CONFIGURATION

    def get_pre_pll_clk_div(self):
        return self.get("pre_pll_clk_div")

    def set_pre_pll_clk_div(self, value):
        return self.set("pre_pll_clk_div", value)

    def get_pll_multiplier(self):
        return self.get("pll_multiplier")

    def set_pll_multiplier(self, value):
        return self.set("pll_multiplier", value)

    def get_vt_sys_clk_div(self):
        return self.get("vt_sys_clk_div")

    def set_vt_sys_clk_div(self, value):
        return self.set("vt_sys_clk_div", value)

    def get_vt_pix_clk_div(self):
        return self.get("vt_pix_clk_div")

    def set_vt_pix_clk_div(self, value):
        return self.set("vt_pix_clk_div", value)

    def get_op_sys_clk_div(self):
        return self.get("op_sys_clk_div")

    def set_op_sys_clk_div(self, value):
        return self.set("op_sys_clk_div", value)

    def get_op_pix_clk_div(self):
        return self.get("op_pix_clk_div")

    def set_op_pix_clk_div(self, value):
        return self.set("op_pix_clk_div", value)

    def _is_clocking_config_valid(self, config):
        if "pre_pll_clk_div" not in config:
            return None
        if config["pre_pll_clk_div"] not in self.get_pre_pll_clk_div_range():
            return False
        config["pll_input_freq_mhz"] = self._ext_clk_freq_mhz / config["pre_pll_clk_div"]
        if config["pll_input_freq_mhz"] not in self.get_pll_input_freq_mhz_range():
            return False
        if "pll_multiplier" not in config:
            return None
        if config["pll_multiplier"] not in self.get_pll_multiplier_range():
            return False
        config["pll_output_freq_mhz"] = config["pll_input_freq_mhz"] * config["pll_multiplier"]
        if config["pll_output_freq_mhz"] not in self.get_pll_output_freq_mhz_range():
            return False
        if "vt_sys_clk_div" not in config:
            return None
        if config["vt_sys_clk_div"] not in self.get_vt_sys_clk_div_range():
            return False
        config["vt_sys_clk_freq_mhz"] = config["pll_output_freq_mhz"] / config["vt_sys_clk_div"]
        if config["vt_sys_clk_freq_mhz"] not in self.get_vt_sys_clk_freq_mhz_range():
            return False
        if "op_sys_clk_div" not in config:
            return None
        if config["op_sys_clk_div"] not in self.get_op_sys_clk_div_range():
            return False
        config["op_sys_clk_freq_mhz"] = config["pll_output_freq_mhz"] / config["op_sys_clk_div"]
        if config["op_sys_clk_freq_mhz"] not in self.get_op_sys_clk_freq_mhz_range():
            return False
        if "vt_pix_clk_div" not in config:
            return None
        if config["vt_pix_clk_div"] not in self.get_vt_pix_clk_div_range():
            return False
        config["vt_pix_clk_freq_mhz"] = config["vt_sys_clk_freq_mhz"] / config["vt_pix_clk_div"]
        if config["vt_pix_clk_freq_mhz"] not in self.get_vt_pix_clk_freq_mhz_range():
            return False
        if "op_pix_clk_div" not in config:
            return None
        if config["op_pix_clk_div"] not in self.get_op_pix_clk_div_range():
            return False
        config["op_pix_clk_freq_mhz"] = config["op_sys_clk_freq_mhz"] / config["op_pix_clk_div"]
        if config["op_pix_clk_freq_mhz"] not in self.get_vt_pix_clk_freq_mhz_range():
            return False
        return True

    def _iter_clocking_configs(self):
        config = {}
        config.update(vt_pix_clk_div=self.get_vt_pix_clk_div())
        config.update(op_pix_clk_div=self.get_op_pix_clk_div())
        for pre_pll_clk_div in reversed(self.get_pre_pll_clk_div_range()):
            config = config.copy()
            config.update(pre_pll_clk_div=pre_pll_clk_div)
            if self._is_clocking_config_valid(config) is False:
                continue
            for pll_multiplier in self.get_pll_multiplier_range():
                config = config.copy()
                config.update(pll_multiplier=pll_multiplier)
                if self._is_clocking_config_valid(config) is False:
                    continue
                for vt_sys_clk_div in reversed(self.get_vt_sys_clk_div_range()):
                    config = config.copy()
                    config.update(vt_sys_clk_div=vt_sys_clk_div)
                    if self._is_clocking_config_valid(config) is False:
                        continue
                    for op_sys_clk_div in reversed(self.get_op_sys_clk_div_range()):
                        config = config.copy()
                        config.update(op_sys_clk_div=op_sys_clk_div)
                        if self._is_clocking_config_valid(config) is False:
                            continue
                        assert self._is_clocking_config_valid(config) is True
                        yield config

    def autoconfigure_clocking(self, constraints=lambda x: True):
        self.set_vt_pix_clk_div(self.get_pixel_depth())
        self.set_op_pix_clk_div(self.get_pixel_depth())
        for config in self._iter_clocking_configs():
            if self._is_clocking_config_valid(config) and constraints(config):
                self.set_pre_pll_clk_div(config["pre_pll_clk_div"])
                self.set_pll_multiplier(config["pll_multiplier"])
                self.set_vt_sys_clk_div(config["vt_sys_clk_div"])
                self.set_op_sys_clk_div(config["op_sys_clk_div"])
                return True
        return False

    def _in_range(self, value, interval):
        if value in interval:
            return ""
        else:
            return " (OUT OF RANGE)"

    def show_clocking_configuration(self):
        self._logger.info("CAMERA CLOCKING CONFIGURATION:")
        self._show("input clock frequency", "%.2f MHz%s",
            self._ext_clk_freq_mhz,
            self._in_range(self._ext_clk_freq_mhz, self.get_ext_clk_freq_mhz_range()))
        pre_pll_clk_div = self.get_pre_pll_clk_div()
        self._show("pre-PLL clock divisor", "%d%s",
            pre_pll_clk_div, self._in_range(pre_pll_clk_div, self.get_pre_pll_clk_div_range()))
        pll_input_freq_mhz = self._ext_clk_freq_mhz / pre_pll_clk_div
        self._show("PLL input frequency", "%.2f MHz%s",
            pll_input_freq_mhz,
            self._in_range(pll_input_freq_mhz, self.get_pll_input_freq_mhz_range()))
        pll_multiplier = self.get_pll_multiplier()
        self._show("PLL multiplier", "%d%s",
            pll_multiplier, self._in_range(pll_multiplier, self.get_pll_multiplier_range()))
        pll_output_freq_mhz = pll_input_freq_mhz * pll_multiplier
        self._show("PLL output frequency", "%.2f MHz%s",
            pll_output_freq_mhz,
            self._in_range(pll_output_freq_mhz, self.get_pll_output_freq_mhz_range()))
        vt_sys_clk_div = self.get_vt_sys_clk_div()
        self._show("video system clock divisor", "%d%s",
            vt_sys_clk_div, self._in_range(vt_sys_clk_div, self.get_vt_sys_clk_div_range()))
        vt_sys_clk_freq_mhz = pll_output_freq_mhz / vt_sys_clk_div
        self._show("video system clock frequency", "%.2f MHz%s",
            vt_sys_clk_freq_mhz,
            self._in_range(vt_sys_clk_freq_mhz, self.get_vt_sys_clk_freq_mhz_range()))
        vt_pix_clk_div = self.get_vt_pix_clk_div()
        self._show("video pixel clock divisor", "%d%s",
            vt_pix_clk_div, self._in_range(vt_pix_clk_div, self.get_vt_pix_clk_div_range()))
        vt_pix_clk_freq_mhz = vt_sys_clk_freq_mhz / vt_pix_clk_div
        self._show("video pixel clock frequency", "%.2f MHz%s",
            vt_pix_clk_freq_mhz,
            self._in_range(vt_pix_clk_freq_mhz, self.get_vt_pix_clk_freq_mhz_range()))
        op_sys_clk_div = self.get_op_sys_clk_div()
        self._show("output system clock divisor", "%d%s",
            op_sys_clk_div, self._in_range(op_sys_clk_div, self.get_op_sys_clk_div_range()))
        op_sys_clk_freq_mhz = pll_output_freq_mhz / op_sys_clk_div
        self._show("output system clock frequency", "%.2f MHz%s",
            op_sys_clk_freq_mhz,
            self._in_range(op_sys_clk_freq_mhz, self.get_op_sys_clk_freq_mhz_range()))
        op_pix_clk_div = self.get_op_pix_clk_div()
        self._show("output pixel clock divisor", "%d%s",
            op_pix_clk_div, self._in_range(op_pix_clk_div, self.get_op_pix_clk_div_range()))
        op_pix_clk_freq_mhz = op_sys_clk_freq_mhz / op_pix_clk_div
        self._show("output pixel clock frequency", "%.2f MHz%s",
            op_pix_clk_freq_mhz,
            self._in_range(op_pix_clk_freq_mhz, self.get_op_pix_clk_freq_mhz_range()))

    # CAMERA INTERFACE CONFIGURATION

    def get_ccp_data_format(self):
        return self.get("ccp_data_format")

    def set_ccp_data_format(self, value):
        self.set("ccp_data_format", value)

    def start_streaming(self):
        self.set("mode_select", 1)

    def stop_streaming(self):
        self.set("mode_select", 0)

    # CAMERA IMAGING CONFIGURATION

    def get_pixel_depth(self):
        return self.get("pixel_depth")

    def show_imaging_configuration(self):
        pass

