# Automatically generated by Amaranth 0.4.dev112+gf96604f. Do not edit.
set -e
[ -n "$AMARANTH_ENV_IceStorm" ] && . "$AMARANTH_ENV_IceStorm"
[ -n "$AMARANTH_ENV_IceStorm" ] && . "$AMARANTH_ENV_IceStorm"
: ${YOSYS:=yosys}
: ${NEXTPNR_ICE40:=nextpnr-ice40}
: ${ICEPACK:=icepack}
"$YOSYS" -q -l top.rpt top.ys
"$NEXTPNR_ICE40" --quiet --placer heap --routed-svg 'nextpnr_test.svg' --log top.tim --hx8k --package bg121 --json top.json --pcf top.pcf --asc top.asc
"$ICEPACK" top.asc top.bin