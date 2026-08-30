# Compila doomgeneric con l'uscita sul DMD al posto di quella su X11.
#
#   make DOOMGENERIC=/percorso/di/doomgeneric/doomgeneric
#
# Il risultato e' un solo binario, `doom-dmd`, che disegna 320x200 in memoria,
# ne ritaglia una fascia, la riduce a 256x64 e la scrive su stdout. Non apre
# finestre, non vuole X, non vuole SDL e non fa suono: sul cabinato l'audio e'
# di Batocera, e un secondo canale sonoro sarebbe solo rumore.
#
# I sorgenti di doomgeneric non stanno in questo repository: sono GPL2 e li
# scarica setup_doom.sh al momento dell'installazione.

DOOMGENERIC ?= /opt/doomgeneric/doomgeneric
OUT ?= doom-dmd
OBJDIR ?= build

CC ?= gcc
# -DDOOMGENERIC_RESX/RESY=320x200: doomgeneric scala di un fattore intero
# (xres / SCREENWIDTH), quindi chiedendogli la risoluzione nativa di Doom il
# fattore e' 1 e non c'e' nessuna scalatura da buttare via subito dopo.
CFLAGS += -O2 -Wall -DNORMALUNIX -DLINUX -D_DEFAULT_SOURCE \
          -DDOOMGENERIC_RESX=320 -DDOOMGENERIC_RESY=200 \
          -I$(DOOMGENERIC)
LDFLAGS +=
LIBS += -lm

SRC_DOOM = dummy.c am_map.c doomdef.c doomstat.c dstrings.c d_event.c \
	d_items.c d_iwad.c d_loop.c d_main.c d_mode.c d_net.c f_finale.c \
	f_wipe.c g_game.c hu_lib.c hu_stuff.c info.c i_cdmus.c i_endoom.c \
	i_joystick.c i_scale.c i_sound.c i_system.c i_timer.c memio.c \
	m_argv.c m_bbox.c m_cheat.c m_config.c m_controls.c m_fixed.c \
	m_menu.c m_misc.c m_random.c p_ceilng.c p_doors.c p_enemy.c \
	p_floor.c p_inter.c p_lights.c p_map.c p_maputl.c p_mobj.c \
	p_plats.c p_pspr.c p_saveg.c p_setup.c p_sight.c p_spec.c \
	p_switch.c p_telept.c p_tick.c p_user.c r_bsp.c r_data.c r_draw.c \
	r_main.c r_plane.c r_segs.c r_sky.c r_things.c sha1.c sounds.c \
	statdump.c st_lib.c st_stuff.c s_sound.c tables.c v_video.c \
	wi_stuff.c w_checksum.c w_file.c w_main.c w_wad.c z_zone.c \
	w_file_stdc.c i_input.c i_video.c doomgeneric.c

OBJS = $(addprefix $(OBJDIR)/, $(SRC_DOOM:.c=.o)) $(OBJDIR)/doomgeneric_dmd.o

all: $(OUT)

$(OUT): $(OBJS)
	$(CC) $(CFLAGS) $(LDFLAGS) $(OBJS) -o $@ $(LIBS)

$(OBJDIR)/doomgeneric_dmd.o: doomgeneric_dmd.c | $(OBJDIR)
	$(CC) $(CFLAGS) -c $< -o $@

$(OBJDIR)/%.o: $(DOOMGENERIC)/%.c | $(OBJDIR)
	$(CC) $(CFLAGS) -c $< -o $@

$(OBJDIR):
	mkdir -p $(OBJDIR)

clean:
	rm -rf $(OBJDIR) $(OUT)

.PHONY: all clean
