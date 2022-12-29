"""The gem representation for Labyrinth on Maze.com."""

import enum
from functools import total_ordering
from typing import Any, Dict, Iterator, Tuple


@total_ordering
class Gem(enum.Enum):
    """One of the gems in the Labyrinth game.

    Note:
        `total_ordering` defines the missing order comparison methods for
        `<=`, `>=`, and `>`, using our implementation for `<` and the default Enum `==`
    """

    ALEXANDRITE_PEAR_SHAPE = "alexandrite-pear-shape"
    ALEXANDRITE = "alexandrite"
    ALMANDINE_GARNET = "almandine-garnet"
    AMETHYST = "amethyst"
    AMETRINE = "ametrine"
    AMMOLITE = "ammolite"
    APATITE = "apatite"
    APLITE = "aplite"
    APRICOT_SQUARE_RADIANT = "apricot-square-radiant"
    AQUAMARINE = "aquamarine"
    AUSTRALIAN_MARQUISE = "australian-marquise"
    AVENTURINE = "aventurine"
    AZURITE = "azurite"
    BERYL = "beryl"
    BLACK_OBSIDIAN = "black-obsidian"
    BLACK_ONYX = "black-onyx"
    BLACK_SPINEL_CUSHION = "black-spinel-cushion"
    BLUE_CEYLON_SAPPHIRE = "blue-ceylon-sapphire"
    BLUE_CUSHION = "blue-cushion"
    BLUE_PEAR_SHAPE = "blue-pear-shape"
    BLUE_SPINEL_HEART = "blue-spinel-heart"
    BULLS_EYE = "bulls-eye"
    CARNELIAN = "carnelian"
    CHROME_DIOPSIDE = "chrome-diopside"
    CHRYSOBERYL_CUSHION = "chrysoberyl-cushion"
    CHRYSOLITE = "chrysolite"
    CITRINE_CHECKERBOARD = "citrine-checkerboard"
    CITRINE = "citrine"
    CLINOHUMITE = "clinohumite"
    COLOR_CHANGE_OVAL = "color-change-oval"
    CORDIERITE = "cordierite"
    DIAMOND = "diamond"
    DUMORTIERITE = "dumortierite"
    EMERALD = "emerald"
    FANCY_SPINEL_MARQUISE = "fancy-spinel-marquise"
    GARNET = "garnet"
    GOLDEN_DIAMOND_CUT = "golden-diamond-cut"
    GOLDSTONE = "goldstone"
    GRANDIDIERITE = "grandidierite"
    GRAY_AGATE = "gray-agate"
    GREEN_AVENTURINE = "green-aventurine"
    GREEN_BERYL_ANTIQUE = "green-beryl-antique"
    GREEN_BERYL = "green-beryl"
    GREEN_PRINCESS_CUT = "green-princess-cut"
    GROSSULAR_GARNET = "grossular-garnet"
    HACKMANITE = "hackmanite"
    HELIOTROPE = "heliotrope"
    HEMATITE = "hematite"
    IOLITE_EMERALD_CUT = "iolite-emerald-cut"
    JASPER = "jasper"
    JASPILITE = "jaspilite"
    KUNZITE_OVAL = "kunzite-oval"
    KUNZITE = "kunzite"
    LABRADORITE = "labradorite"
    LAPIS_LAZULI = "lapis-lazuli"
    LEMON_QUARTZ_BRIOLETTE = "lemon-quartz-briolette"
    MAGNESITE = "magnesite"
    MEXICAN_OPAL = "mexican-opal"
    MOONSTONE = "moonstone"
    MORGANITE_OVAL = "morganite-oval"
    MOSS_AGATE = "moss-agate"
    ORANGE_RADIANT = "orange-radiant"
    PADPARADSCHA_OVAL = "padparadscha-oval"
    PADPARADSCHA_SAPPHIRE = "padparadscha-sapphire"
    PERIDOT = "peridot"
    PINK_EMERALD_CUT = "pink-emerald-cut"
    PINK_OPAL = "pink-opal"
    PINK_ROUND = "pink-round"
    PINK_SPINEL_CUSHION = "pink-spinel-cushion"
    PRASIOLITE = "prasiolite"
    PREHNITE = "prehnite"
    PURPLE_CABOCHON = "purple-cabochon"
    PURPLE_OVAL = "purple-oval"
    PURPLE_SPINEL_TRILLION = "purple-spinel-trillion"
    PURPLE_SQUARE_CUSHION = "purple-square-cushion"
    RAW_BERYL = "raw-beryl"
    RAW_CITRINE = "raw-citrine"
    RED_DIAMOND = "red-diamond"
    RED_SPINEL_SQUARE_EMERALD_CUT = "red-spinel-square-emerald-cut"
    RHODONITE = "rhodonite"
    ROCK_QUARTZ = "rock-quartz"
    ROSE_QUARTZ = "rose-quartz"
    RUBY_DIAMOND_PROFILE = "ruby-diamond-profile"
    RUBY = "ruby"
    SPHALERITE = "sphalerite"
    SPINEL = "spinel"
    STAR_CABOCHON = "star-cabochon"
    STILBITE = "stilbite"
    SUNSTONE = "sunstone"
    SUPER_SEVEN = "super-seven"
    TANZANITE_TRILLION = "tanzanite-trillion"
    TIGERS_EYE = "tigers-eye"
    TOURMALINE_LASER_CUT = "tourmaline-laser-cut"
    TOURMALINE = "tourmaline"
    UNAKITE = "unakite"
    WHITE_SQUARE = "white-square"
    YELLOW_BAGUETTE = "yellow-baguette"
    YELLOW_BERYL_OVAL = "yellow-beryl-oval"
    YELLOW_HEART = "yellow-heart"
    YELLOW_JASPER = "yellow-jasper"
    ZIRCON = "zircon"
    ZOISITE = "zoisite"

    def __lt__(self, other: Any) -> bool:
        """Returns true if `other` is a Gem and it's name is alphabetically after this gem's."""
        if not isinstance(other, Gem):
            raise TypeError("Gems are only comparable with other gems")
        return self.value < other.value

    @classmethod
    def from_string(cls, name: str) -> "Gem":
        """Gets the gem with the given name.

        Raises:
            KeyError: if `name` is not the name of a gem
        """
        name_to_instance: Dict[str, Gem] = {e.value: e for e in cls}
        return name_to_instance[name]

    @staticmethod
    def unordered_pairs() -> Iterator[Tuple["Gem", "Gem"]]:
        """Loops through the full list of unordered pairs of gems.

        Yields:
            Iterator[Tuple[Gem, Gem]]: Pairs of gems; in each one the minimum of the pair is first.
        """
        all_gems = sorted(Gem)
        for idx1, gem1 in enumerate(all_gems):
            for idx2 in range(idx1 + 1, len(all_gems)):
                # `gem1` can be paired with any gems after it without making
                # any duplicates when compared as unordered pairs
                yield (gem1, all_gems[idx2])
