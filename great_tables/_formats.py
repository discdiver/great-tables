from __future__ import annotations
from decimal import Decimal
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    ClassVar,
    TypeVar,
    Union,
    List,
    Tuple,
    cast,
    Optional,
    Dict,
    Literal,
)
from typing_extensions import TypeAlias
from ._tbl_data import PlExpr, SelectExpr, is_na
from ._gt_data import GTData, FormatFns, FormatFn, FormatInfo
from ._locale import _get_locales_data, _get_default_locales_data, _get_currencies_data
from ._locations import resolve_rows_i, resolve_cols_c
from ._text import _md_html
from ._utils import _str_detect, _str_replace
from ._utils_nanoplots import _generate_nanoplot
import pandas as pd
import math
from datetime import datetime, date, time
from babel.dates import format_date, format_time, format_datetime
from pathlib import Path


if TYPE_CHECKING:
    from ._types import GTSelf

T = TypeVar("T")
DateStyle: TypeAlias = Literal[
    "iso",
    "wday_month_day_year",
    "wd_m_day_year",
    "wday_day_month_year",
    "month_day_year",
    "m_day_year",
    "day_m_year",
    "day_month_year",
    "day_month",
    "day_m",
    "year",
    "month",
    "day",
    "year.mn.day",
    "y.mn.day",
    "year_week",
    "year_quarter",
]
TimeStyle: TypeAlias = Literal[
    "iso",
    "iso-short",
    "h_m_s_p",
    "h_m_p",
    "h_p",
]
PlotType: TypeAlias = Literal[
    "line",
    "bar",
]
MissingVals: TypeAlias = Literal[
    "marker",
    "gap",
    "zero",
    "remove",
]


def fmt(
    self: GTSelf,
    fns: Union[FormatFn, FormatFns],
    columns: SelectExpr = None,
    rows: Union[int, List[int], None] = None,
    is_substitution=False,
) -> GTSelf:
    """
    Set a column format with a formatter function.

    The `fmt()` method provides a way to execute custom formatting functionality with raw data
    values in a way that can consider all output contexts.

    Along with the `columns` and `rows` arguments that provide some precision in targeting data
    cells, the `fns` argument allows you to define one or more functions for manipulating the
    raw data.

    Parameters
    ----------
    fns
        Either a single formatting function or a named list of functions.
    columns
        The columns to target. Can either be a single column name or a series of column names
        provided in a list.
    rows
        In conjunction with `columns=`, we can specify which of their rows should undergo
        formatting. The default is all rows, resulting in all rows in `columns` being formatted.
        Alternatively, we can supply a list of row indices.
    is_substitution
        Whether the formatter is a substitution. Substitutions are run last, after other formatters.

    Returns
    -------
    GT
        The GT object is returned. This is the same object that the method is called on so that we
        can facilitate method chaining.
    """

    # If a single function is supplied to `fns` then
    # repackage that into a list as the `default` function
    if isinstance(fns, Callable):
        fns = FormatFns(default=fns)

    row_res = resolve_rows_i(self, rows)
    row_pos = [name_pos[1] for name_pos in row_res]

    col_res = resolve_cols_c(self, columns)

    formatter = FormatInfo(fns, col_res, row_pos)

    if is_substitution:
        return self._replace(_substitutions=[*self._substitutions, formatter])

    return self._replace(_formats=[*self._formats, formatter])


def fmt_number(
    self: GTSelf,
    columns: SelectExpr = None,
    rows: Union[int, List[int], None] = None,
    decimals: int = 2,
    n_sigfig: Optional[int] = None,
    drop_trailing_zeros: bool = False,
    drop_trailing_dec_mark: bool = True,
    use_seps: bool = True,
    scale_by: float = 1,
    compact: bool = False,
    pattern: str = "{x}",
    sep_mark: str = ",",
    dec_mark: str = ".",
    force_sign: bool = False,
    locale: Union[str, None] = None,
) -> GTSelf:
    """
    Format numeric values.

    With numeric values within a table's body cells, we can perform number-based formatting so that
    the targeted values are rendered with a higher consideration for tabular presentation.
    Furthermore, there is finer control over numeric formatting with the following options:

    - decimals: choice of the number of decimal places, option to drop trailing zeros, and a choice
    of the decimal symbol
    - digit grouping separators: options to enable/disable digit separators and provide a choice of
    separator symbol
    - scaling: we can choose to scale targeted values by a multiplier value
    - large-number suffixing: larger figures (thousands, millions, etc.) can be autoscaled and
    decorated with the appropriate suffixes
    - pattern: option to use a text pattern for decoration of the formatted values
    - locale-based formatting: providing a locale ID will result in number formatting specific to
    the chosen locale

    Parameters
    ----------
    columns
        The columns to target. Can either be a single column name or a series of column names
        provided in a list.
    rows
        In conjunction with `columns=`, we can specify which of their rows should undergo
        formatting. The default is all rows, resulting in all rows in targeted columns being
        formatted. Alternatively, we can supply a list of row indices.
    decimals
        The `decimals` values corresponds to the exact number of decimal places to use. A value such
        as `2.34` can, for example, be formatted with `0` decimal places and it would result in
        `"2"`. With `4` decimal places, the formatted value becomes `"2.3400"`. The trailing zeros
        can be removed with `drop_trailing_zeros=True`. If you always need `decimals = 0`, the
        [`fmt_integer()`](`great_tables.GT.fmt_integer`) method should be considered.
    n_sigfig
        A option to format numbers to *n* significant figures. By default, this is `None` and thus
        number values will be formatted according to the number of decimal places set via
        `decimals`. If opting to format according to the rules of significant figures, `n_sigfig`
        must be a number greater than or equal to `1`. Any values passed to the `decimals` and
        `drop_trailing_zeros` arguments will be ignored.
    drop_trailing_zeros
        A boolean value that allows for removal of trailing zeros (those redundant zeros after the
        decimal mark).
    drop_trailing_dec_mark
        A boolean value that determines whether decimal marks should always appear even if there are
        no decimal digits to display after formatting (e.g., `23` becomes `23.` if `False`). By
        default trailing decimal marks are not shown.
    use_seps
        The `use_seps` option allows for the use of digit group separators. The type of digit group
        separator is set by `sep_mark` and overridden if a locale ID is provided to `locale`. This
        setting is `True` by default.
    scale_by
        All numeric values will be multiplied by the `scale_by` value before undergoing formatting.
        Since the `default` value is `1`, no values will be changed unless a different multiplier
        value is supplied.
    compact
        A boolean value that allows for compact formatting of numeric values. Values will be scaled
        and decorated with the appropriate suffixes (e.g., `1230` becomes `1.23K`, and `1230000`
        becomes `1.23M`). The `compact` option is `False` by default.
    pattern
        A formatting pattern that allows for decoration of the formatted value. The formatted value
        is represented by the `{x}` (which can be used multiple times, if needed) and all other
        characters will be interpreted as string literals.
    sep_mark
        The string to use as a separator between groups of digits. For example, using `sep_mark=","`
        with a value of `1000` would result in a formatted value of `"1,000"`. This argument is
        ignored if a `locale` is supplied (i.e., is not `None`).
    dec_mark
        The string to be used as the decimal mark. For example, using `dec_mark=","` with the value
        `0.152` would result in a formatted value of `"0,152"`). This argument is ignored if a
        `locale` is supplied (i.e., is not `None`).
    force_sign
        Should the positive sign be shown for positive values (effectively showing a sign for all
        values except zero)? If so, use `True` for this option. The default is `False`, where only
        negative numbers will display a minus sign. This option is disregarded when using accounting
        notation with `accounting = True`.
    locale
        An optional locale identifier that can be used for formatting values according the locale's
        rules. Examples include `"en"` for English (United States) and `"fr"` for French (France).

    Returns
    -------
    GT
        The GT object is returned. This is the same object that the method is called on so that we
        can facilitate method chaining.

    Adapting output to a specific `locale`
    --------------------------------------
    This formatting method can adapt outputs according to a provided `locale` value. Examples
    include `"en"` for English (United States) and `"fr"` for French (France). The use of a valid
    locale ID here means separator and decimal marks will be correct for the given locale. Should
    any values be provided in `sep_mark` or `dec_mark`, they will be overridden by the locale's
    preferred values.

    Note that a `locale` value provided here will override any global locale setting performed in
    [`GT()`](`great_tables.GT`)'s own `locale` argument (it is settable there as a value received by
    all other methods that have a `locale` argument).

    Examples
    --------
    Let's use the `exibble` dataset to create a table. With the `fmt_number()` method, we'll format
    the `num` column to have three decimal places (with `decimals=3`) and omit the use of digit
    separators (with `use_seps=False`).

    ```{python}
    from great_tables import GT, exibble

    (
        GT(exibble)
        .fmt_number(columns="num", decimals=3, use_seps=False)
    )
    ```

    See Also
    --------
    The [`fmt_integer()`](`great_tables.GT.fmt_integer`) method might be more useful if you really
    need to format numeric values to appear as integers (i.e., no decimals will be shown and input
    values are rounded as necessary). Need to do numeric formatting on a value or list of values?
    Take a look at the functional version of this method:
    [`val_fmt_number()`](`great_tables._formats_vals.val_fmt_number`).
    """

    # Stop if `locale` does not have a valid value; normalize locale and resolve one
    # that might be set globally
    _validate_locale(locale=locale)
    locale = _normalize_locale(locale=locale)
    locale = _resolve_locale(self, locale=locale)

    # Use locale-based marks if a locale ID is provided
    sep_mark = _get_locale_sep_mark(default=sep_mark, use_seps=use_seps, locale=locale)
    dec_mark = _get_locale_dec_mark(default=dec_mark, locale=locale)

    # Generate a function that will operate on single `x` values in the table body
    def fmt_number_fn(
        x: float,
        decimals: int = decimals,
        n_sigfig: Optional[int] = n_sigfig,
        drop_trailing_zeros: bool = drop_trailing_zeros,
        drop_trailing_dec_mark: bool = drop_trailing_dec_mark,
        use_seps: bool = use_seps,
        scale_by: float = scale_by,
        compact: bool = compact,
        sep_mark: str = sep_mark,
        dec_mark: str = dec_mark,
        force_sign: bool = force_sign,
    ):
        # Scale `x` value by a defined `scale_by` value
        x = x * scale_by

        # Determine whether the value is positive
        is_negative = _has_negative_value(value=x)

        if compact:
            x_formatted = _format_number_compactly(
                value=x,
                decimals=decimals,
                n_sigfig=n_sigfig,
                drop_trailing_zeros=drop_trailing_zeros,
                drop_trailing_dec_mark=drop_trailing_dec_mark,
                use_seps=use_seps,
                sep_mark=sep_mark,
                dec_mark=dec_mark,
                force_sign=force_sign,
            )
        else:
            x_formatted = _value_to_decimal_notation(
                value=x,
                decimals=decimals,
                n_sigfig=n_sigfig,
                drop_trailing_zeros=drop_trailing_zeros,
                drop_trailing_dec_mark=drop_trailing_dec_mark,
                use_seps=use_seps,
                sep_mark=sep_mark,
                dec_mark=dec_mark,
                force_sign=force_sign,
            )

        # Implement minus sign replacement for `x_formatted`
        if is_negative:
            minus_mark = _context_minus_mark()
            x_formatted = _replace_minus(x_formatted, minus_mark=minus_mark)

        # Use a supplied pattern specification to decorate the formatted value
        if pattern != "{x}":
            x_formatted = pattern.replace("{x}", x_formatted)

        return x_formatted

    return fmt(self, fns=fmt_number_fn, columns=columns, rows=rows)


def fmt_integer(
    self: GTSelf,
    columns: SelectExpr = None,
    rows: Union[int, List[int], None] = None,
    use_seps: bool = True,
    scale_by: float = 1,
    compact: bool = False,
    pattern: str = "{x}",
    sep_mark: str = ",",
    force_sign: bool = False,
    locale: Union[str, None] = None,
) -> GTSelf:
    """
    Format values as integers.

    With numeric values in one or more table columns, we can perform number-based formatting so that
    the targeted values are always rendered as integer values.

    We can have fine control over integer formatting with the following options:

    - digit grouping separators: options to enable/disable digit separators and provide a choice of
    separator symbol
    - scaling: we can choose to scale targeted values by a multiplier value
    - large-number suffixing: larger figures (thousands, millions, etc.) can be autoscaled and
    decorated with the appropriate suffixes
    - pattern: option to use a text pattern for decoration of the formatted values
    - locale-based formatting: providing a locale ID will result in number formatting specific to
    the chosen locale

    Parameters
    ----------
    columns
        The columns to target. Can either be a single column name or a series of column names
        provided in a list.
    rows
        In conjunction with `columns=`, we can specify which of their rows should undergo
        formatting. The default is all rows, resulting in all rows in targeted columns being
        formatted. Alternatively, we can supply a list of row indices.
    use_seps
        The `use_seps` option allows for the use of digit group separators. The type of digit group
        separator is set by `sep_mark` and overridden if a locale ID is provided to `locale`. This
        setting is `True` by default.
    scale_by
        All numeric values will be multiplied by the `scale_by` value before undergoing formatting.
        Since the `default` value is `1`, no values will be changed unless a different multiplier
        value is supplied.
    compact
        A boolean value that allows for compact formatting of numeric values. Values will be scaled
        and decorated with the appropriate suffixes (e.g., `1230` becomes `1K`, and `1230000`
        becomes `1M`). The `compact` option is `False` by default.
    pattern
        A formatting pattern that allows for decoration of the formatted value. The formatted value
        is represented by the `{x}` (which can be used multiple times, if needed) and all other
        characters will be interpreted as string literals.
    sep_mark
        The string to use as a separator between groups of digits. For example, using `sep_mark=","`
        with a value of `1000` would result in a formatted value of `"1,000"`. This argument is
        ignored if a `locale` is supplied (i.e., is not `None`).
    force_sign
        Should the positive sign be shown for positive values (effectively showing a sign for all
        values except zero)? If so, use `True` for this option. The default is `False`, where only
        negative numbers will display a minus sign. This option is disregarded when using accounting
        notation with `accounting = True`.
    locale
        An optional locale identifier that can be used for formatting values according the locale's
        rules. Examples include `"en"` for English (United States) and `"fr"` for French (France).

    Returns
    -------
    GT
        The GT object is returned. This is the same object that the method is called on so that we
        can facilitate method chaining.

    Adapting output to a specific `locale`
    --------------------------------------
    This formatting method can adapt outputs according to a provided `locale` value. Examples
    include `"en"` for English (United States) and `"fr"` for French (France). The use of a valid
    locale ID here means separator marks will be correct for the given locale. Should any value be
    provided in `sep_mark`, it will be overridden by the locale's preferred value.

    Note that a `locale` value provided here will override any global locale setting performed in
    [`GT()`](`great_tables.GT`)'s own `locale` argument (it is settable there as a value received by
    all other methods that have a `locale` argument).

    Examples
    --------
    For this example, we'll use the `exibble` dataset as the input table. With the `fmt_integer()`
    method, we'll format the `num` column as integer values having no digit separators (with the
    `use_seps=False` option).

    ```{python}
    from great_tables import GT, exibble

    (
        GT(exibble)
        .fmt_integer(columns="num", use_seps=False)
    )
    ```

    See Also
    --------
    The [`fmt_number()`](`great_tables.GT.fmt_number`) method might be more of what you need if
    you'd like decimal values in your outputs. Need to do integer-based formatting on a value or
    list of values? Take a look at the functional version of this method:
    [`val_fmt_integer()`](`great_tables._formats_vals.val_fmt_integer`).
    """

    # Stop if `locale` does not have a valid value; normalize locale and resolve one
    # that might be set globally
    _validate_locale(locale=locale)
    locale = _normalize_locale(locale=locale)

    # Use locale-based marks if a locale ID is provided
    sep_mark = _get_locale_sep_mark(default=sep_mark, use_seps=use_seps, locale=locale)

    # Generate a function that will operate on single `x` values in
    # the table body
    def fmt_integer_fn(
        x: float,
        scale_by: float = scale_by,
    ):
        # If the `x` value is a Pandas 'NA', then return the same value
        if pd.isna(x):
            return x

        # Scale `x` value by a defined `scale_by` value
        x = x * scale_by

        # Determine whether the value is positive
        is_negative = _has_negative_value(value=x)

        if compact:
            x_formatted = _format_number_compactly(
                value=x,
                decimals=0,
                n_sigfig=None,
                drop_trailing_zeros=False,
                drop_trailing_dec_mark=True,
                use_seps=use_seps,
                sep_mark=sep_mark,
                dec_mark="not used",
                force_sign=force_sign,
            )
        else:
            x_formatted = _value_to_decimal_notation(
                value=x,
                decimals=0,
                n_sigfig=None,
                drop_trailing_zeros=False,
                drop_trailing_dec_mark=True,
                use_seps=use_seps,
                sep_mark=sep_mark,
                dec_mark="not used",
                force_sign=force_sign,
            )

        # Implement minus sign replacement for `x_formatted`
        if is_negative:
            minus_mark = _context_minus_mark()
            x_formatted = _replace_minus(x_formatted, minus_mark=minus_mark)

        # Use a supplied pattern specification to decorate the formatted value
        if pattern != "{x}":
            x_formatted = pattern.replace("{x}", x_formatted)

        return x_formatted

    return fmt(self, fns=fmt_integer_fn, columns=columns, rows=rows)


def fmt_scientific(
    self: GTSelf,
    columns: SelectExpr = None,
    rows: Union[int, List[int], None] = None,
    decimals: int = 2,
    n_sigfig: Optional[int] = None,
    drop_trailing_zeros: bool = False,
    drop_trailing_dec_mark: bool = True,
    scale_by: float = 1,
    exp_style: str = "x10n",
    pattern: str = "{x}",
    sep_mark: str = ",",
    dec_mark: str = ".",
    force_sign_m: bool = False,
    force_sign_n: bool = False,
    locale: Union[str, None] = None,
) -> GTSelf:
    """
    Format values to scientific notation.

    With numeric values in a table, we can perform formatting so that the targeted values are
    rendered in scientific notation, where extremely large or very small numbers can be expressed in
    a more practical fashion. Here, numbers are written in the form of a mantissa (`m`) and an
    exponent (`n`) with the construction *m* x 10^*n* or *m*E*n*. The mantissa component is a number
    between `1` and `10`. For instance, `2.5 x 10^9` can be used to represent the value
    2,500,000,000 in scientific notation. In a similar way, 0.00000012 can be expressed as
    `1.2 x 10^-7`. Due to its ability to describe numbers more succinctly and its ease of
    calculation, scientific notation is widely employed in scientific and technical domains.

    We have fine control over the formatting task, with the following options:

    - decimals: choice of the number of decimal places, option to drop trailing zeros, and a choice
    of the decimal symbol
    - scaling: we can choose to scale targeted values by a multiplier value
    - pattern: option to use a text pattern for decoration of the formatted values
    - locale-based formatting: providing a locale ID will result in formatting specific to the
    chosen locale

    Parameters
    ----------
    columns
        The columns to target. Can either be a single column name or a series of column names
        provided in a list.
    rows
        In conjunction with `columns=`, we can specify which of their rows should undergo
        formatting. The default is all rows, resulting in all rows in targeted columns being
        formatted. Alternatively, we can supply a list of row indices.
    decimals
        The `decimals` values corresponds to the exact number of decimal places to use. A value such
        as `2.34` can, for example, be formatted with `0` decimal places and it would result in
        `"2"`. With `4` decimal places, the formatted value becomes `"2.3400"`. The trailing zeros
        can be removed with `drop_trailing_zeros=True`.
    n_sigfig
        A option to format numbers to *n* significant figures. By default, this is `None` and thus
        number values will be formatted according to the number of decimal places set via
        `decimals`. If opting to format according to the rules of significant figures, `n_sigfig`
        must be a number greater than or equal to `1`. Any values passed to the `decimals` and
        `drop_trailing_zeros` arguments will be ignored.
    drop_trailing_zeros
        A boolean value that allows for removal of trailing zeros (those redundant zeros after the
        decimal mark).
    drop_trailing_dec_mark
        A boolean value that determines whether decimal marks should always appear even if there are
        no decimal digits to display after formatting (e.g., `23` becomes `23.` if `False`). By
        default trailing decimal marks are not shown.
    scale_by
        All numeric values will be multiplied by the `scale_by` value before undergoing formatting.
        Since the `default` value is `1`, no values will be changed unless a different multiplier
        value is supplied.
    exp_style
        Style of formatting to use for the scientific notation formatting. By default this is
        `"x10n"` but other options include using a single letter (e.g., `"e"`, `"E"`, etc.), a
        letter followed by a `"1"` to signal a minimum digit width of one, or `"low-ten"` for using
        a stylized `"10"` marker.
    pattern
        A formatting pattern that allows for decoration of the formatted value. The formatted value
        is represented by the `{x}` (which can be used multiple times, if needed) and all other
        characters will be interpreted as string literals.
    sep_mark
        The string to use as a separator between groups of digits. For example, using `sep_mark=","`
        with a value of `1000` would result in a formatted value of `"1,000"`. This argument is
        ignored if a `locale` is supplied (i.e., is not `None`).
    dec_mark
        The string to be used as the decimal mark. For example, using `dec_mark=","` with the value
        `0.152` would result in a formatted value of `"0,152"`). This argument is ignored if a
        `locale` is supplied (i.e., is not `None`).
    force_sign_m
        Should the plus sign be shown for positive values of the mantissa (first component)? This
        would effectively show a sign for all values except zero on the first numeric component of
        the notation. If so, use `True` (the default for this is `False`), where only negative
        numbers will display a sign.
    force_sign_n
        Should the plus sign be shown for positive values of the exponent (second component)? This
        would effectively show a sign for all values except zero on the second numeric component of
        the notation. If so, use `True` (the default for this is `False`), where only negative
        numbers will display a sign.
    locale
        An optional locale identifier that can be used for formatting values according the locale's
        rules. Examples include `"en"` for English (United States) and `"fr"` for French (France).

    Returns
    -------
    GT
        The GT object is returned. This is the same object that the method is called on so that we
        can facilitate method chaining.

    Adapting output to a specific `locale`
    --------------------------------------
    This formatting method can adapt outputs according to a provided `locale` value. Examples
    include `"en"` for English (United States) and `"fr"` for French (France). The use of a valid
    locale ID here means separator and decimal marks will be correct for the given locale. Should
    any values be provided in `sep_mark` or `dec_mark`, they will be overridden by the locale's
    preferred values.

    Note that a `locale` value provided here will override any global locale setting performed in
    [`GT()`](`great_tables.GT`)'s own `locale` argument (it is settable there as a value received by
    all other methods that have a `locale` argument).

    Examples
    --------
    For this example, we'll use the `exibble` dataset as the input table. With the
    `fmt_scientific()` method, we'll format the `num` column to contain values in scientific
    formatting.

    ```{python}
    from great_tables import GT, exibble

    (
        GT(exibble)
        .fmt_scientific(columns="num")
    )
    ```

    See Also
    --------
    The functional version of this method,
    [`val_fmt_scientific()`](`great_tables._formats_vals.val_fmt_scientific`), allows you to format
    a single numerical value (or a list of them).
    """

    # Set a default value for `use_seps`; these separators are only used for very
    # large exponent values
    use_seps = True

    # Stop if `locale` does not have a valid value; normalize locale and resolve one
    # that might be set globally
    _validate_locale(locale=locale)
    locale = _normalize_locale(locale=locale)

    # Use locale-based marks if a locale ID is provided
    sep_mark = _get_locale_sep_mark(default=sep_mark, use_seps=use_seps, locale=locale)
    dec_mark = _get_locale_dec_mark(default=dec_mark, locale=locale)

    # Generate a function that will operate on single `x` values in the table body
    def fmt_scientific_fn(
        x: float,
        decimals: int = decimals,
        n_sigfig: Optional[int] = n_sigfig,
        drop_trailing_zeros: bool = drop_trailing_zeros,
        drop_trailing_dec_mark: bool = drop_trailing_dec_mark,
        scale_by: float = scale_by,
        exp_style: str = exp_style,
        sep_mark: str = sep_mark,
        dec_mark: str = dec_mark,
        force_sign_m: bool = force_sign_m,
        force_sign_n: bool = force_sign_n,
    ):
        # If the `x` value is a Pandas 'NA', then return the same value
        if pd.isna(x):
            return x

        # Scale `x` value by a defined `scale_by` value
        x = x * scale_by

        # Determine whether the value is positive
        is_positive = _has_positive_value(value=x)

        minus_mark = _context_minus_mark()

        x_sci_notn = _value_to_scientific_notation(
            value=x,
            decimals=decimals,
            n_sigfig=n_sigfig,
            dec_mark=dec_mark,
        )

        sci_parts = x_sci_notn.split("E")

        m_part = sci_parts[0]
        n_part = sci_parts[1]

        # Remove trailing zeros and decimal marks from the `m_part`
        if drop_trailing_zeros:
            m_part = m_part.rstrip("0")
        if drop_trailing_dec_mark:
            m_part = m_part.rstrip(".")

        # Force the positive sign to be present if the `force_sign_m` option is taken
        if is_positive and force_sign_m:
            m_part = "+" + m_part

        if exp_style == "x10n":
            # Define the exponent string based on the `exp_style` that is the default
            # ('x10n'); this is styled as 'x 10^n' instead of using a fixed symbol like 'E'

            # Determine which values don't require the (x 10^n) for scientific formatting
            # since their order would be zero
            small_pos = _has_sci_order_zero(value=x)

            # Force the positive sign to be present if the `force_sign_n` option is taken
            if force_sign_n and not _str_detect(n_part, "-"):
                n_part = "+" + n_part

            # Implement minus sign replacement for `m_part` and `n_part`
            m_part = _replace_minus(m_part, minus_mark=minus_mark)
            n_part = _replace_minus(n_part, minus_mark=minus_mark)

            if small_pos:
                # If the value is small enough to not require the (x 10^n) notation, then
                # the formatted value is based on only the `m_part`
                x_formatted = m_part
            else:
                # Get the set of exponent marks, which are used to decorate the `n_part`
                exp_marks = _context_exp_marks()

                # Create the formatted string based on `exp_marks` and the two `sci_parts`
                x_formatted = m_part + exp_marks[0] + n_part + exp_marks[1]

        else:
            # Define the exponent string based on the `exp_style` that's not the default
            # value of 'x10n'

            exp_str = _context_exp_str(exp_style=exp_style)

            n_min_width = 1 if _str_detect(exp_style, r"^[a-zA-Z]1$") else 2

            # The `n_part` will be extracted here and it must be padded to
            # the defined minimum number of decimal places
            if _str_detect(n_part, "-"):
                n_part = _str_replace(n_part, "-", "")
                n_part = n_part.ljust(n_min_width, "0")
                n_part = "-" + n_part
            else:
                n_part = n_part.ljust(n_min_width, "0")
                if force_sign_n:
                    n_part = "+" + n_part

            # Implement minus sign replacement for `m_part` and `n_part`
            m_part = _replace_minus(m_part, minus_mark=minus_mark)
            n_part = _replace_minus(n_part, minus_mark=minus_mark)

            x_formatted = m_part + exp_str + n_part

        # Use a supplied pattern specification to decorate the formatted value
        if pattern != "{x}":
            x_formatted = pattern.replace("{x}", x_formatted)

        return x_formatted

    return fmt(self, fns=fmt_scientific_fn, columns=columns, rows=rows)


def fmt_percent(
    self: GTSelf,
    columns: SelectExpr = None,
    rows: Union[int, List[int], None] = None,
    decimals: int = 2,
    drop_trailing_zeros: bool = False,
    drop_trailing_dec_mark: bool = True,
    scale_values: bool = True,
    use_seps: bool = True,
    pattern: str = "{x}",
    sep_mark: str = ",",
    dec_mark: str = ".",
    force_sign: bool = False,
    placement: str = "right",
    incl_space: bool = False,
    locale: Union[str, None] = None,
) -> GTSelf:
    """
    Format values as a percentage.

    With numeric values in a **gt** table, we can perform percentage-based formatting. It is assumed
    the input numeric values are proportional values and, in this case, the values will be
    automatically multiplied by `100` before decorating with a percent sign (the other case is
    accommodated though setting `scale_values` to `False`). For more control over percentage
    formatting, we can use the following options:

    - percent sign placement: the percent sign can be placed after or before the values and a space
    can be inserted between the symbol and the value.
    - decimals: choice of the number of decimal places, option to drop trailing zeros, and a choice
    of the decimal symbol
    - digit grouping separators: options to enable/disable digit separators and provide a choice of
    separator symbol
    - value scaling toggle: choose to disable automatic value scaling in the situation that values
    are already scaled coming in (and just require the percent symbol)
    - pattern: option to use a text pattern for decoration of the formatted values
    - locale-based formatting: providing a locale ID will result in number formatting specific to
    the chosen locale

    Parameters
    ----------
    columns
        The columns to target. Can either be a single column name or a series of column names
        provided in a list.
    rows
        In conjunction with `columns=`, we can specify which of their rows should undergo
        formatting. The default is all rows, resulting in all rows in targeted columns being
        formatted. Alternatively, we can supply a list of row indices.
    decimals
        The `decimals` values corresponds to the exact number of decimal places to use. A value such
        as `2.34` can, for example, be formatted with `0` decimal places and it would result in
        `"2"`. With `4` decimal places, the formatted value becomes `"2.3400"`. The trailing zeros
        can be removed with `drop_trailing_zeros=True`.
    drop_trailing_zeros
        A boolean value that allows for removal of trailing zeros (those redundant zeros after the
        decimal mark).
    drop_trailing_dec_mark
        A boolean value that determines whether decimal marks should always appear even if there are
        no decimal digits to display after formatting (e.g., `23` becomes `23.` if `False`). By
        default trailing decimal marks are not shown.
    scale_values
        Should the values be scaled through multiplication by 100? By default this scaling is
        performed since the expectation is that incoming values are usually proportional. Setting to
        `False` signifies that the values are already scaled and require only the percent sign when
        formatted.
    use_seps
        The `use_seps` option allows for the use of digit group separators. The type of digit group
        separator is set by `sep_mark` and overridden if a locale ID is provided to `locale`. This
        setting is `True` by default.
    pattern
        A formatting pattern that allows for decoration of the formatted value. The formatted value
        is represented by the `{x}` (which can be used multiple times, if needed) and all other
        characters will be interpreted as string literals.
    sep_mark
        The string to use as a separator between groups of digits. For example, using `sep_mark=","`
        with a value of `1000` would result in a formatted value of `"1,000"`. This argument is
        ignored if a `locale` is supplied (i.e., is not `None`).
    dec_mark
        The string to be used as the decimal mark. For example, using `dec_mark=","` with the value
        `0.152` would result in a formatted value of `"0,152"`). This argument is ignored if a
        `locale` is supplied (i.e., is not `None`).
    force_sign
        Should the positive sign be shown for positive values (effectively showing a sign for all
        values except zero)? If so, use `True` for this option. The default is `False`, where only
        negative numbers will display a minus sign. This option is disregarded when using accounting
        notation with `accounting = True`.
    placement
        This option governs the placement of the percent sign. This can be either be `"right"` (the
        default) or `"left"`.
    incl_space
        An option for whether to include a space between the value and the percent sign. The default
        is to not introduce a space character.
    locale
        An optional locale identifier that can be used for formatting values according the locale's
        rules. Examples include `"en"` for English (United States) and `"fr"` for French (France).

    Returns
    -------
    GT
        The GT object is returned. This is the same object that the method is called on so that we
        can facilitate method chaining.

    Adapting output to a specific `locale`
    --------------------------------------
    This formatting method can adapt outputs according to a provided `locale` value. Examples
    include `"en"` for English (United States) and `"fr"` for French (France). The use of a valid
    locale ID here means separator and decimal marks will be correct for the given locale. Should
    any values be provided in `sep_mark` or `dec_mark`, they will be overridden by the locale's
    preferred values.

    Note that a `locale` value provided here will override any global locale setting performed in
    [`GT()`](`great_tables.GT`)'s own `locale` argument (it is settable there as a value received by
    all other methods that have a `locale` argument).

    See Also
    --------
    The functional version of this method,
    [`val_fmt_percent()`](`great_tables._formats_vals.val_fmt_percent`), allows you to format a
    single numerical value (or a list of them).
    """

    # Stop if `locale` does not have a valid value; normalize locale and resolve one
    # that might be set globally
    _validate_locale(locale=locale)
    locale = _normalize_locale(locale=locale)

    # Use locale-based marks if a locale ID is provided
    sep_mark = _get_locale_sep_mark(default=sep_mark, use_seps=use_seps, locale=locale)
    dec_mark = _get_locale_dec_mark(default=dec_mark, locale=locale)

    if scale_values:
        scale_by = 100.0
    else:
        scale_by = 1.0

    # Generate a function that will operate on single `x` values in the table body
    def fmt_percent_fn(
        x: float,
        decimals: int = decimals,
        drop_trailing_zeros: bool = drop_trailing_zeros,
        drop_trailing_dec_mark: bool = drop_trailing_dec_mark,
        use_seps: bool = use_seps,
        scale_by: float = scale_by,
        sep_mark: str = sep_mark,
        dec_mark: str = dec_mark,
        force_sign: bool = force_sign,
        placement: str = placement,
        incl_space: bool = incl_space,
    ):
        # If the `x` value is a Pandas 'NA', then return the same value
        if pd.isna(x):
            return x

        # Scale `x` value by a defined `scale_by` value
        x = x * scale_by

        # Determine properties of the value
        is_negative = _has_negative_value(value=x)
        is_positive = _has_positive_value(value=x)

        x_formatted = _value_to_decimal_notation(
            value=x,
            decimals=decimals,
            n_sigfig=None,
            drop_trailing_zeros=drop_trailing_zeros,
            drop_trailing_dec_mark=drop_trailing_dec_mark,
            use_seps=use_seps,
            sep_mark=sep_mark,
            dec_mark=dec_mark,
            force_sign=force_sign,
        )

        # Create a percent pattern for affixing the percent sign
        space_character = " " if incl_space else ""
        percent_pattern = (
            f"{{x}}{space_character}%" if placement == "right" else f"%{space_character}{{x}}"
        )

        if is_negative and placement == "left":
            x_formatted = x_formatted.replace("-", "")
            x_formatted = percent_pattern.replace("{x}", x_formatted)
            x_formatted = "-" + x_formatted
        elif is_positive and force_sign and placement == "left":
            x_formatted = x_formatted.replace("+", "")
            x_formatted = percent_pattern.replace("{x}", x_formatted)
            x_formatted = "+" + x_formatted
        else:
            x_formatted = percent_pattern.replace("{x}", x_formatted)

        # Implement minus sign replacement for `x_formatted`
        if is_negative:
            minus_mark = _context_minus_mark()
            x_formatted = _replace_minus(x_formatted, minus_mark=minus_mark)

        # Use a supplied pattern specification to decorate the formatted value
        if pattern != "{x}":
            x_formatted = pattern.replace("{x}", x_formatted)

        return x_formatted

    return fmt(self, fns=fmt_percent_fn, columns=columns, rows=rows)


def fmt_currency(
    self: GTSelf,
    columns: SelectExpr = None,
    rows: Union[int, List[int], None] = None,
    currency: Optional[str] = None,
    use_subunits: bool = True,
    decimals: Optional[int] = None,
    drop_trailing_dec_mark: bool = True,
    use_seps: bool = True,
    scale_by: float = 1,
    pattern: str = "{x}",
    sep_mark: str = ",",
    dec_mark: str = ".",
    force_sign: bool = False,
    placement: str = "left",
    incl_space: bool = False,
    locale: Union[str, None] = None,
) -> GTSelf:
    """
    Format values as currencies.

    With numeric values in a **gt** table, we can perform currency-based formatting with the
    `fmt_currency()` method. This supports both automatic formatting with a three-letter currency
    code. We have fine control over the conversion from numeric values to currency values, where we
    could take advantage of the following options:

    - the currency: providing a currency code or common currency name will procure the correct
    currency symbol and number of currency subunits
    - currency symbol placement: the currency symbol can be placed before or after the values
    - decimals/subunits: choice of the number of decimal places, and a choice of the decimal symbol,
    and an option on whether to include or exclude the currency subunits (the decimal portion)
    - digit grouping separators: options to enable/disable digit separators and provide a choice of
    separator symbol
    - scaling: we can choose to scale targeted values by a multiplier value
    - pattern: option to use a text pattern for decoration of the formatted currency values
    - locale-based formatting: providing a locale ID will result in currency formatting specific to
    the chosen locale; it will also retrieve the locale's currency if none is explicitly given

    Parameters
    ----------
    columns
        The columns to target. Can either be a single column name or a series of column names
        provided in a list.
    rows
        In conjunction with `columns=`, we can specify which of their rows should undergo
        formatting. The default is all rows, resulting in all rows in targeted columns being
        formatted. Alternatively, we can supply a list of row indices.
    currency
        The currency to use for the numeric value. This input can be supplied as a 3-letter currency
        code (e.g., `"USD"` for U.S. Dollars, `"EUR"` for the Euro currency).
    use_subunits
        An option for whether the subunits portion of a currency value should be displayed. For
        example, with an input value of `273.81`, the default formatting will produce `"$273.81"`.
        Removing the subunits (with `use_subunits = False`) will give us `"$273"`.
    decimals
        The `decimals` values corresponds to the exact number of decimal places to use. This value
        is optional as a currency has an intrinsic number of decimal places (i.e., the subunits).
        A value such as `2.34` can, for example, be formatted with `0` decimal places and if the
        currency used is `"USD"` it would result in `"$2"`. With `4` decimal places, the formatted
        value becomes `"$2.3400"`.
    drop_trailing_dec_mark
        A boolean value that determines whether decimal marks should always appear even if there are
        no decimal digits to display after formatting (e.g., `23` becomes `23.` if `False`). By
        default trailing decimal marks are not shown.
    use_seps
        The `use_seps` option allows for the use of digit group separators. The type of digit group
        separator is set by `sep_mark` and overridden if a locale ID is provided to `locale`. This
        setting is `True` by default.
    scale_by
        All numeric values will be multiplied by the `scale_by` value before undergoing formatting.
        Since the `default` value is `1`, no values will be changed unless a different multiplier
        value is supplied.
    pattern
        A formatting pattern that allows for decoration of the formatted value. The formatted value
        is represented by the `{x}` (which can be used multiple times, if needed) and all other
        characters will be interpreted as string literals.
    sep_mark
        The string to use as a separator between groups of digits. For example, using `sep_mark=","`
        with a value of `1000` would result in a formatted value of `"1,000"`. This argument is
        ignored if a `locale` is supplied (i.e., is not `None`).
    dec_mark
        The string to be used as the decimal mark. For example, using `dec_mark=","` with the value
        `0.152` would result in a formatted value of `"0,152"`). This argument is ignored if a
        `locale` is supplied (i.e., is not `None`).
    force_sign
        Should the positive sign be shown for positive values (effectively showing a sign for all
        values except zero)? If so, use `True` for this option. The default is `False`, where only
        negative numbers will display a minus sign. This option is disregarded when using accounting
        notation with `accounting = True`.
    placement
        The placement of the currency symbol. This can be either be `"left"` (as in `"$450"`) or
        `"right"` (which yields `"450$"`).
    incl_space
        An option for whether to include a space between the value and the currency symbol. The
        default is to not introduce a space character.
    locale
        An optional locale identifier that can be used for formatting values according the locale's
        rules. Examples include `"en"` for English (United States) and `"fr"` for French (France).

    Returns
    -------
    GT
        The GT object is returned. This is the same object that the method is called on so that we
        can facilitate method chaining.

    Adapting output to a specific `locale`
    --------------------------------------
    This formatting method can adapt outputs according to a provided `locale` value. Examples
    include `"en"` for English (United States) and `"fr"` for French (France). The use of a valid
    locale ID here means separator and decimal marks will be correct for the given locale. Should
    any values be provided in `sep_mark` or `dec_mark`, they will be overridden by the locale's
    preferred values. In addition to number formatting, providing a `locale` value and not providing
    a `currency` allows **Great Tables** to obtain the currency code from the locale's territory.

    Note that a `locale` value provided here will override any global locale setting performed in
    [`GT()`](`great_tables.GT`)'s own `locale` argument (it is settable there as a value received by
    all other methods that have a `locale` argument).

    Examples
    --------
    Let's use the `exibble` dataset to create a table. With the `fmt_currency()` method, we'll
    format the `currency` column to display monetary values.

    ```{python}
    from great_tables import GT, exibble

    (
        GT(exibble)
        .fmt_currency(
            columns="currency",
            decimals=3,
            use_seps=False
        )
    )
    ```

    See Also
    --------
    The functional version of this method,
    [`val_fmt_currency()`](`great_tables._formats_vals.val_fmt_currency`), allows you to format a
    single numerical value (or a list of them).
    """

    # Stop if `locale` does not have a valid value; normalize locale and resolve one
    # that might be set globally
    _validate_locale(locale=locale)
    locale = _normalize_locale(locale=locale)

    # Use locale-based marks if a locale ID is provided
    sep_mark = _get_locale_sep_mark(default=sep_mark, use_seps=use_seps, locale=locale)
    dec_mark = _get_locale_dec_mark(default=dec_mark, locale=locale)

    # Resolve the currency either from direct input in `currency` or through a locale
    if currency is None:
        # If not providing a `currency` code, we can obtain the currency code from the locale
        currency_resolved = _get_locale_currency_code(locale=locale)
    else:
        # Cast the `currency` value to a string
        currency_resolved = str(currency)
        # Stop if `currency_resolved` does not have a valid value
        _validate_currency(currency=currency_resolved)

    # Get the number of decimal places for the currency; this takes into account whether
    # the currency uses subunits or not and whether decimals are explicitly set
    decimals = _get_currency_decimals(
        currency=currency_resolved, decimals=decimals, use_subunits=use_subunits
    )

    # Generate a function that will operate on single `x` values in the table body
    def fmt_currency_fn(
        x: float,
        currency: str = currency_resolved,
        decimals: int = decimals,
        drop_trailing_dec_mark: bool = drop_trailing_dec_mark,
        use_seps: bool = use_seps,
        scale_by: float = scale_by,
        sep_mark: str = sep_mark,
        dec_mark: str = dec_mark,
        force_sign: bool = force_sign,
        placement: str = placement,
        incl_space: bool = incl_space,
    ):
        # If the `x` value is a Pandas 'NA', then return the same value
        if pd.isna(x):
            return x

        # Scale `x` value by a defined `scale_by` value
        x = x * scale_by

        # Determine properties of the value
        is_negative = _has_negative_value(value=x)
        is_positive = _has_positive_value(value=x)

        # Get the currency symbol on the basis of a valid currency code
        currency_symbol = _get_currency_str(currency=currency)

        # Format the value to decimal notation; this is done before the currency symbol is
        # affixed to the value
        x_formatted = _value_to_decimal_notation(
            value=x,
            decimals=decimals,
            n_sigfig=None,
            drop_trailing_zeros=False,
            drop_trailing_dec_mark=drop_trailing_dec_mark,
            use_seps=use_seps,
            sep_mark=sep_mark,
            dec_mark=dec_mark,
            force_sign=force_sign,
        )

        # Create a currency pattern for affixing the currency symbol
        space_character = " " if incl_space else ""
        currency_pattern = (
            f"{{x}}{space_character}{currency_symbol}"
            if placement == "right"
            else f"{currency_symbol}{space_character}{{x}}"
        )

        if is_negative and placement == "left":
            x_formatted = x_formatted.replace("-", "")
            x_formatted = currency_pattern.replace("{x}", x_formatted)
            x_formatted = "-" + x_formatted
        elif is_positive and force_sign and placement == "left":
            x_formatted = x_formatted.replace("+", "")
            x_formatted = currency_pattern.replace("{x}", x_formatted)
            x_formatted = "+" + x_formatted
        else:
            x_formatted = currency_pattern.replace("{x}", x_formatted)

        # Implement minus sign replacement for `x_formatted`
        if is_negative:
            minus_mark = _context_minus_mark()
            x_formatted = _replace_minus(x_formatted, minus_mark=minus_mark)

        # Use a supplied pattern specification to decorate the formatted value
        if pattern != "{x}":
            x_formatted = pattern.replace("{x}", x_formatted)

        return x_formatted

    return fmt(self, fns=fmt_currency_fn, columns=columns, rows=rows)


def fmt_roman(
    self: GTSelf,
    columns: SelectExpr = None,
    rows: Union[int, List[int], None] = None,
    case: str = "upper",
    pattern: str = "{x}",
) -> GTSelf:
    """
    Format values as Roman numerals.

    With numeric values in a **gt** table we can transform those to Roman numerals, rounding values
    as necessary.

    Parameters
    ----------
    columns
        The columns to target. Can either be a single column name or a series of column names
        provided in a list.
    rows
        In conjunction with `columns=`, we can specify which of their rows should undergo
        formatting. The default is all rows, resulting in all rows in targeted columns being
        formatted. Alternatively, we can supply a list of row indices.
    case
        Should Roman numerals should be rendered as uppercase (`"upper"`) or lowercase (`"lower"`)
        letters? By default, this is set to `"upper"`.
    pattern
        A formatting pattern that allows for decoration of the formatted value. The formatted value
        is represented by the `{x}` (which can be used multiple times, if needed) and all other
        characters will be interpreted as string literals.

    Returns
    -------
    GT
        The GT object is returned. This is the same object that the method is called on so that we
        can facilitate method chaining.

    Examples
    --------
    Let's first create a DataFrame containing small numeric values and then introduce that to
    [`GT()`](`great_tables.GT`). We'll then format the `roman` column to appear as Roman numerals
    with the `fmt_roman()` method.

    ```{python}
    import pandas as pd
    from great_tables import GT

    numbers_tbl = pd.DataFrame({"arabic": [1, 8, 24, 85], "roman": [1, 8, 24, 85]})

    (
        GT(numbers_tbl, rowname_col="arabic")
        .fmt_roman(columns="roman")
    )
    ```

    See Also
    --------
    The functional version of this method,
    [`val_fmt_roman()`](`great_tables._formats_vals.val_fmt_roman`), allows you to format a single
    numerical value (or a list of them).
    """

    # Check that the `case` value is valid and only consists of the string 'upper' or 'lower'
    _validate_case(case=case)

    # Generate a function that will operate on single `x` values in the table body
    def fmt_roman_fn(
        x: float,
        case: str = case,
    ):
        # If the `x` value is a Pandas 'NA', then return the same value
        if pd.isna(x):
            return x

        # Get the absolute value of `x` so that negative values are handled
        x = abs(x)

        # Round x to 0 digits with the R-H-U method of rounding (for reproducibility purposes)
        x = _round_rhu(x, 0)

        # Determine if `x` is in the range of 1 to 3899 and if it is zero
        x_is_in_range = x > 0 and x < 3900
        x_is_zero = x == 0

        if not x_is_in_range and not x_is_zero:
            # We cannot format a 'large' integer to roman numerals, so we return a string
            # that indicates this
            return "ex terminis"
        elif x_is_zero:
            # Zero is a special case and is handled separately with the character 'N'
            # which stands for 'nulla' (i.e., 'nothing')
            x_formatted = "N"
        else:
            # All other values are formatted with the `_as_roman()` utility function
            x_formatted = _as_roman(x)

        # Transform the case of the formatted value
        if case == "upper":
            pass
        else:
            x_formatted = x_formatted.lower()

        # Use a supplied pattern specification to decorate the formatted value
        if pattern != "{x}":
            x_formatted = pattern.replace("{x}", x_formatted)

        return x_formatted

    return fmt(self, fns=fmt_roman_fn, columns=columns, rows=rows)


def fmt_bytes(
    self: GTSelf,
    columns: SelectExpr = None,
    rows: Union[int, List[int], None] = None,
    standard: str = "decimal",
    decimals: int = 1,
    n_sigfig: Optional[int] = None,
    drop_trailing_zeros: bool = True,
    drop_trailing_dec_mark: bool = True,
    use_seps: bool = True,
    pattern: str = "{x}",
    sep_mark: str = ",",
    dec_mark: str = ".",
    force_sign: bool = False,
    incl_space: bool = True,
    locale: Union[str, None] = None,
) -> GTSelf:
    """
    Format values as bytes.

    With numeric values in a table, we can transform those to values of bytes with human readable
    units. The `fmt_bytes()` method allows for the formatting of byte sizes to either of two common
    representations: (1) with decimal units (powers of 1000, examples being `"kB"` and `"MB"`), and
    (2) with binary units (powers of 1024, examples being `"KiB"` and `"MiB"`). It is assumed the
    input numeric values represent the number of bytes and automatic truncation of values will
    occur. The numeric values will be scaled to be in the range of 1 to <1000 and then decorated
    with the correct unit symbol according to the standard chosen. For more control over the
    formatting of byte sizes, we can use the following options:

    - decimals: choice of the number of decimal places, option to drop trailing zeros, and a choice
    of the decimal symbol
    - digit grouping separators: options to enable/disable digit separators and provide a choice of
    separator symbol
    - pattern: option to use a text pattern for decoration of the formatted values
    - locale-based formatting: providing a locale ID will result in number formatting specific to
    the chosen locale

    Parameters
    ----------
    columns
        The columns to target. Can either be a single column name or a series of column names
        provided in a list.
    rows
        In conjunction with `columns=`, we can specify which of their rows should undergo
        formatting. The default is all rows, resulting in all rows in targeted columns being
        formatted. Alternatively, we can supply a list of row indices.
    standard
        The form of expressing large byte sizes is divided between: (1) decimal units (powers of
        1000; e.g., `"kB"` and `"MB"`), and (2) binary units (powers of 1024; e.g., `"KiB"` and
        `"MiB"`). The default is to use decimal units with the `"decimal"` option. The alternative
        is to use binary units with the `"binary"` option.
    decimals
        This corresponds to the exact number of decimal places to use. A value such as `2.34` can,
        for example, be formatted with `0` decimal places and it would result in `"2"`. With `4`
        decimal places, the formatted value becomes `"2.3400"`. The trailing zeros can be removed
        with `drop_trailing_zeros=True`.
    drop_trailing_zeros
        A boolean value that allows for removal of trailing zeros (those redundant zeros after the
        decimal mark).
    drop_trailing_dec_mark
        A boolean value that determines whether decimal marks should always appear even if there are
        no decimal digits to display after formatting (e.g., `23` becomes `23.` if `False`). By
        default trailing decimal marks are not shown.
    use_seps
        The `use_seps` option allows for the use of digit group separators. The type of digit group
        separator is set by `sep_mark` and overridden if a locale ID is provided to `locale`. This
        setting is `True` by default.
    pattern
        A formatting pattern that allows for decoration of the formatted value. The formatted value
        is represented by the `{x}` (which can be used multiple times, if needed) and all other
        characters will be interpreted as string literals.
    sep_mark
        The string to use as a separator between groups of digits. For example, using `sep_mark=","`
        with a value of `1000` would result in a formatted value of `"1,000"`. This argument is
        ignored if a `locale` is supplied (i.e., is not `None`).
    dec_mark
        The string to be used as the decimal mark. For example, using `dec_mark=","` with the value
        `0.152` would result in a formatted value of `"0,152"`). This argument is ignored if a
        `locale` is supplied (i.e., is not `None`).
    force_sign
        Should the positive sign be shown for positive values (effectively showing a sign for all
        values except zero)? If so, use `True` for this option. The default is `False`, where only
        negative numbers will display a minus sign. This option is disregarded when using accounting
        notation with `accounting = True`.
    incl_space
        An option for whether to include a space between the value and the currency symbol. The
        default is to not introduce a space character.
    locale
        An optional locale identifier that can be used for formatting values according the locale's
        rules. Examples include `"en"` for English (United States) and `"fr"` for French (France).

    Returns
    -------
    GT
        The GT object is returned. This is the same object that the method is called on so that we
        can facilitate method chaining.

    Adapting output to a specific `locale`
    --------------------------------------
    This formatting method can adapt outputs according to a provided `locale` value. Examples
    include `"en"` for English (United States) and `"fr"` for French (France). The use of a valid
    locale ID here means separator and decimal marks will be correct for the given locale. Should
    any values be provided in `sep_mark` or `dec_mark`, they will be overridden by the locale's
    preferred values.

    Note that a `locale` value provided here will override any global locale setting performed in
    [`GT()`](`great_tables.GT`)'s own `locale` argument (it is settable there as a value received by
    all other methods that have a `locale` argument).

    Examples
    --------
    Let's use a single column from the `exibble` dataset and create a new table. We'll format the
    `num` column to display as byte sizes in the decimal standard through use of the `fmt_bytes()`
    method.

    ```{python}
    from great_tables import GT, exibble

    (
        GT(exibble[["num"]])
        .fmt_bytes(columns="num", standard="decimal")
    )
    ```

    See Also
    --------
    The functional version of this method,
    [`val_fmt_bytes()`](`great_tables._formats_vals.val_fmt_bytes`), allows you to format a single
    numerical value (or a list of them).
    """

    # Stop if `locale` does not have a valid value; normalize locale and resolve one
    # that might be set globally
    _validate_locale(locale=locale)
    locale = _normalize_locale(locale=locale)

    # Use locale-based marks if a locale ID is provided
    sep_mark = _get_locale_sep_mark(default=sep_mark, use_seps=use_seps, locale=locale)
    dec_mark = _get_locale_dec_mark(default=dec_mark, locale=locale)

    # Stop if `n_sigfig` does not have a valid value
    if n_sigfig is not None:
        _validate_n_sigfig(n_sigfig=n_sigfig)

    # Get the `base` value and the `byte_units` list based on the `standard` value
    if standard == "decimal":
        # This is the 'decimal' standard (the default)
        base = 1000
        byte_units = ["B", "kB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB"]
    else:
        # This is the 'binary' standard
        base = 1024
        byte_units = ["B", "KiB", "MiB", "GiB", "TiB", "PiB", "EiB", "ZiB", "YiB"]

    # Generate a function that will operate on single `x` values in the table body
    def fmt_bytes_fn(
        x: float,
        base: int = base,
        byte_units: List[str] = byte_units,
        decimals: int = decimals,
        n_sigfig: Optional[int] = n_sigfig,
        drop_trailing_zeros: bool = drop_trailing_zeros,
        drop_trailing_dec_mark: bool = drop_trailing_dec_mark,
        use_seps: bool = use_seps,
        sep_mark: str = sep_mark,
        dec_mark: str = dec_mark,
        force_sign: bool = force_sign,
        incl_space: bool = incl_space,
    ):
        # If the `x` value is a Pandas 'NA', then return the same value
        if pd.isna(x):
            return x

        # Truncate all byte values by casting to an integer; this is done because bytes
        # are always whole numbers
        x = int(x)

        # Determine properties of the value
        is_negative = _has_negative_value(value=x)

        # Determine the power index for the value
        if x == 0:
            # If the value is zero, then the power index is 1; otherwise, we'd get
            # an error when trying to calculate the log of zero
            num_power_idx = 1
        else:
            # Otherwise, we can calculate the power index by taking the log of the value
            # and dividing by the log of the base; we add 1 to the result to account for
            # the fact that the power index is 1-based (i.e., the first element in the
            # `byte_units` list is at index 0) --- the final statement ensures that the
            # power index is always at least 1
            num_power_idx = math.floor(math.log(abs(x), base)) + 1
            num_power_idx = max(1, min(len(byte_units), num_power_idx))

        # The `units_str` is obtained by indexing the `byte_units` list with the `num_power_idx`
        # value; this is the string that will be affixed to the formatted value
        units_str = byte_units[num_power_idx - 1]

        # Scale `x` value by a defined `base` value, this is done by dividing by the
        # `base` value raised to the power index minus 1 (we subtract 1 because the
        # power index is 1-based)
        x = x / base ** (num_power_idx - 1)

        # Format the value to decimal notation; this is done before the `byte_units` text
        # is affixed to the value
        x_formatted = _value_to_decimal_notation(
            value=x,
            decimals=decimals,
            n_sigfig=n_sigfig,
            drop_trailing_zeros=drop_trailing_zeros,
            drop_trailing_dec_mark=drop_trailing_dec_mark,
            use_seps=use_seps,
            sep_mark=sep_mark,
            dec_mark=dec_mark,
            force_sign=force_sign,
        )

        # Create a `bytes_pattern` object for affixing the `units_str`, which is the
        # string that represents the byte units
        space_character = " " if incl_space else ""
        bytes_pattern = f"{{x}}{space_character}{units_str}"

        x_formatted = bytes_pattern.replace("{x}", x_formatted)

        # Implement minus sign replacement for `x_formatted`
        if is_negative:
            minus_mark = _context_minus_mark()
            x_formatted = _replace_minus(x_formatted, minus_mark=minus_mark)

        # Use a supplied pattern specification to decorate the formatted value
        if pattern != "{x}":
            x_formatted = pattern.replace("{x}", x_formatted)

        return x_formatted

    return fmt(self, fns=fmt_bytes_fn, columns=columns, rows=rows)


def fmt_date(
    self: GTSelf,
    columns: SelectExpr = None,
    rows: Union[int, List[int], None] = None,
    date_style: DateStyle = "iso",
    pattern: str = "{x}",
    locale: Union[str, None] = None,
) -> GTSelf:
    """
    Format values as dates.

    Format input values to time values using one of 17 preset date styles. Input can be in the form
    of `date` type or as a ISO-8601 string (in the form of `YYYY-MM-DD HH:MM:SS` or `YYYY-MM-DD`).

    Parameters
    ----------
    columns
        The columns to target. Can either be a single column name or a series of column names
        provided in a list.
    rows
        In conjunction with `columns=`, we can specify which of their rows should undergo
        formatting. The default is all rows, resulting in all rows in targeted columns being
        formatted. Alternatively, we can supply a list of row indices.
    date_style
        The date style to use. By default this is the short name `"iso"` which corresponds to
        ISO 8601 date formatting. There are 41 date styles in total and their short names can be
        viewed using `info_date_style()`.
    pattern
        A formatting pattern that allows for decoration of the formatted value. The formatted value
        is represented by the `{x}` (which can be used multiple times, if needed) and all other
        characters will be interpreted as string literals.
    locale
        An optional locale identifier that can be used for formatting values according the locale's
        rules. Examples include `"en"` for English (United States) and `"fr"` for French (France).

    Formatting with the `date_style` argument
    -----------------------------------------
    We need to supply a preset date style to the `date_style` argument. The date styles are numerous
    and can handle localization to any supported locale. The following table provides a listing of
    all date styles and their output values (corresponding to an input date of `2000-02-29`).

    |    | Date Style            | Output                  |
    |----|-----------------------|-------------------------|
    | 1  | `"iso"`               | `"2000-02-29"`          |
    | 2  | `"wday_month_day_year"`| `"Tuesday, February 29, 2000"`  |
    | 3  | `"wd_m_day_year"`     | `"Tue, Feb 29, 2000"`   |
    | 4  | `"wday_day_month_year"`| `"Tuesday 29 February 2000"`    |
    | 5  | `"month_day_year"`    | `"February 29, 2000"`   |
    | 6  | `"m_day_year"`        | `"Feb 29, 2000"`        |
    | 7  | `"day_m_year"`        | `"29 Feb 2000"`         |
    | 8  | `"day_month_year"`    | `"29 February 2000"`    |
    | 9  | `"day_month"`         | `"29 February"`         |
    | 10 | `"day_m"`             | `"29 Feb"`              |
    | 11 | `"year"`              | `"2000"`                |
    | 12 | `"month"`             | `"February"`            |
    | 13 | `"day"`               | `"29"`                  |
    | 14 | `"year.mn.day"`       | `"2000/02/29"`          |
    | 15 | `"y.mn.day"`          | `"00/02/29"`            |
    | 16 | `"year_week"`         | `"2000-W09"`            |
    | 17 | `"year_quarter"`      | `"2000-Q1"`             |

    We can use the `info_date_style()` function within the console to view a similar table of date
    styles with example output.

    Returns
    -------
    GT
        The GT object is returned. This is the same object that the method is called on so that we
        can facilitate method chaining.

    Adapting output to a specific `locale`
    --------------------------------------
    This formatting method can adapt outputs according to a provided `locale` value. Examples
    include `"en"` for English (United States) and `"fr"` for French (France). Note that a `locale`
    value provided here will override any global locale setting performed in
    [`GT()`](`great_tables.GT`)'s own `locale` argument (it is settable there as a value received by
    all other methods that have a `locale` argument).

    Examples
    --------
    Let's use the `exibble` dataset to create a simple, two-column table (keeping only the `date`
    and `time` columns). With the `fmt_date()` method, we'll format the `date` column to display
    dates formatted with the `"month_day_year"` date style.

    ```{python}
    from great_tables import GT, exibble

    exibble_mini = exibble[["date", "time"]]

    (
        GT(exibble_mini)
        .fmt_date(columns="date", date_style="month_day_year")
    )
    ```

    See Also
    --------
    The functional version of this method,
    [`val_fmt_date()`](`great_tables._formats_vals.val_fmt_date`), allows you to format a single
    numerical value (or a list of them).
    """

    # Stop if `locale` does not have a valid value; normalize locale and resolve one
    # that might be set globally
    _validate_locale(locale=locale)
    locale = _normalize_locale(locale=locale)

    # Get the date format string based on the `date_style` value
    date_format_str = _get_date_format(date_style=date_style)

    # Generate a function that will operate on single `x` values in the table body
    def fmt_date_fn(
        x: Any, date_format_str: str = date_format_str, locale: Union[str, None] = locale
    ) -> str:
        # If the `x` value is a Pandas 'NA', then return the same value
        if pd.isna(x):
            return x

        # If `x` is a string, we assume it is an ISO date string and convert it to a date object
        if isinstance(x, str):
            # Stop if `x` is not a valid ISO date string
            _validate_iso_date_str(x=x)

            # Convert the ISO date string to a date object
            x = _iso_to_date(x)

        else:
            # Stop if `x` is not a valid date object
            _validate_date_obj(x=x)

        # Fix up the locale for `format_date()` by replacing any hyphens with underscores
        if locale is None:
            locale = "en_US"
        else:
            locale = _str_replace(locale, "-", "_")

        # Format the date object to a string using Babel's `format_date()` function
        x_formatted = format_date(x, format=date_format_str, locale=locale)

        # Use a supplied pattern specification to decorate the formatted value
        if pattern != "{x}":
            x_formatted = pattern.replace("{x}", x_formatted)

        return x_formatted

    return fmt(self, fns=fmt_date_fn, columns=columns, rows=rows)


def fmt_time(
    self: GTSelf,
    columns: SelectExpr = None,
    rows: Union[int, List[int], None] = None,
    time_style: TimeStyle = "iso",
    pattern: str = "{x}",
    locale: Union[str, None] = None,
) -> GTSelf:
    """
    Format values as times.

    Format input values to time values using one of 5 preset time styles. Input can be in the form
    of `time` values, or strings in the ISO 8601 forms of `HH:MM:SS` or `YYYY-MM-DD HH:MM:SS`.

    Parameters
    ----------
    columns
        The columns to target. Can either be a single column name or a series of column names
        provided in a list.
    rows
        In conjunction with `columns=`, we can specify which of their rows should undergo
        formatting. The default is all rows, resulting in all rows in targeted columns being
        formatted. Alternatively, we can supply a list of row indices.
    time_style
        The time style to use. By default this is the short name `"iso"` which corresponds to how
        times are formatted within ISO 8601 datetime values. There are 5 time styles in total and
        their short names can be viewed using `info_time_style()`.
    pattern
        A formatting pattern that allows for decoration of the formatted value. The formatted value
        is represented by the `{x}` (which can be used multiple times, if needed) and all other
        characters will be interpreted as string literals.
    locale
        An optional locale identifier that can be used for formatting values according the locale's
        rules. Examples include `"en"` for English (United States) and `"fr"` for French (France).

    Formatting with the `time_style` argument
    -----------------------------------------
    We need to supply a preset time style to the `time_style` argument. The time styles are numerous
    and can handle localization to any supported locale. The following table provides a listing of
    all time styles and their output values (corresponding to an input time of `14:35:00`).

    |    | Time Style    | Output                          | Notes         |
    |----|---------------|---------------------------------|---------------|
    | 1  | `"iso"`       | `"14:35:00"`                    | ISO 8601, 24h |
    | 2  | `"iso-short"` | `"14:35"`                       | ISO 8601, 24h |
    | 3  | `"h_m_s_p"`   | `"2:35:00 PM"`                  | 12h           |
    | 4  | `"h_m_p"`     | `"2:35 PM"`                     | 12h           |
    | 5  | `"h_p"`       | `"2 PM"`                        | 12h           |

    We can use the `info_time_style()` function within the console to view a similar table of time
    styles with example output.

    Returns
    -------
    GT
        The GT object is returned. This is the same object that the method is called on so that we
        can facilitate method chaining.

    Adapting output to a specific `locale`
    --------------------------------------
    This formatting method can adapt outputs according to a provided `locale` value. Examples
    include `"en"` for English (United States) and `"fr"` for French (France). Note that a `locale`
    value provided here will override any global locale setting performed in
    [`GT()`](`great_tables.GT`)'s own `locale` argument (it is settable there as a value received by
    all other methods that have a `locale` argument).

    Examples
    --------
    Let's use the `exibble` dataset to create a simple, two-column table (keeping only the `date`
    and `time` columns). With the `fmt_time()` method, we'll format the `time` column to display
    times formatted with the `"h_m_s_p"` time style.

    ```{python}
    from great_tables import GT, exibble

    exibble_mini = exibble[["date", "time"]]

    (
        GT(exibble_mini)
        .fmt_time(columns="time", time_style="h_m_s_p")
    )
    ```

    See Also
    --------
    The functional version of this method,
    [`val_fmt_time()`](`great_tables._formats_vals.val_fmt_time`), allows you to format a single
    numerical value (or a list of them).
    """

    # Stop if `locale` does not have a valid value; normalize locale and resolve one
    # that might be set globally
    _validate_locale(locale=locale)
    locale = _normalize_locale(locale=locale)

    # Get the time format string based on the `time_style` value
    time_format_str = _get_time_format(time_style=time_style)

    # Generate a function that will operate on single `x` values in the table body
    def fmt_time_fn(
        x: Any, time_format_str: str = time_format_str, locale: Union[str, None] = locale
    ) -> str:
        # If the `x` value is a Pandas 'NA', then return the same value
        if pd.isna(x):
            return x

        # If `x` is a string, assume it is an ISO time string and convert it to a time object
        if isinstance(x, str):
            # Stop if `x` is not a valid ISO time string
            _validate_iso_time_str(x=x)

            # Ensure that a seconds value is present in the ISO time string
            x = _normalize_iso_time_str(x=x)

            # Convert the ISO time string to a time object
            x = _iso_to_time(x)

        else:
            # Stop if `x` is not a valid time object
            _validate_time_obj(x=x)

        # Fix up the locale for `format_time()` by replacing any hyphens with underscores
        if locale is None:
            locale = "en_US"
        else:
            locale = _str_replace(locale, "-", "_")

        # Format the time object to a string using Babel's `format_time()` function
        x_formatted = format_time(x, format=time_format_str, locale=locale)

        # Use a supplied pattern specification to decorate the formatted value
        if pattern != "{x}":
            x_formatted = pattern.replace("{x}", x_formatted)

        return x_formatted

    return fmt(self, fns=fmt_time_fn, columns=columns, rows=rows)


def fmt_datetime(
    self: GTSelf,
    columns: SelectExpr = None,
    rows: Union[int, List[int], None] = None,
    date_style: DateStyle = "iso",
    time_style: TimeStyle = "iso",
    sep: str = " ",
    pattern: str = "{x}",
    locale: Union[str, None] = None,
) -> GTSelf:
    """
    Format values as datetimes.

    Format input values to datetime values using one of 17 preset date styles and one of 5 preset
    time styles. Input can be in the form of `datetime` values, or strings in the ISO 8601 forms of
    `YYYY-MM-DD HH:MM:SS` or `YYYY-MM-DD`.

    Parameters
    ----------
    columns
        The columns to target. Can either be a single column name or a series of column names
        provided in a list.
    rows
        In conjunction with `columns=`, we can specify which of their rows should undergo
        formatting. The default is all rows, resulting in all rows in targeted columns being
        formatted. Alternatively, we can supply a list of row indices.
    date_style
        The date style to use. By default this is the short name `"iso"` which corresponds to
        ISO 8601 date formatting. There are 41 date styles in total and their short names can be
        viewed using `info_date_style()`.
    time_style
        The time style to use. By default this is the short name `"iso"` which corresponds to how
        times are formatted within ISO 8601 datetime values. There are 5 time styles in total and
        their short names can be viewed using `info_time_style()`.

    Formatting with the `date_style` and `time_style` arguments
    ------------------------------------------------------------
    We need to supply a preset date style to the `date_style` argument and a preset time style to
    the `time_style` argument. The date styles are numerous and can handle localization to any
    supported locale. The following table provides a listing of all date styles and their output
    values (corresponding to an input date of `2000-02-29 14:35:00`).

    |    | Date Style            | Output                  |
    |----|-----------------------|-------------------------|
    | 1  | `"iso"`               | `"2000-02-29"`          |
    | 2  | `"wday_month_day_year"`| `"Tuesday, February 29, 2000"`  |
    | 3  | `"wd_m_day_year"`     | `"Tue, Feb 29, 2000"`   |
    | 4  | `"wday_day_month_year"`| `"Tuesday 29 February 2000"`    |
    | 5  | `"month_day_year"`    | `"February 29, 2000"`   |
    | 6  | `"m_day_year"`        | `"Feb 29, 2000"`        |
    | 7  | `"day_m_year"`        | `"29 Feb 2000"`         |
    | 8  | `"day_month_year"`    | `"29 February 2000"`    |
    | 9  | `"day_month"`         | `"29 February"`         |
    | 10 | `"day_m"`             | `"29 Feb"`              |
    | 11 | `"year"`              | `"2000"`                |
    | 12 | `"month"`             | `"February"`            |
    | 13 | `"day"`               | `"29"`                  |
    | 14 | `"year.mn.day"`       | `"2000/02/29"`          |
    | 15 | `"y.mn.day"`          | `"00/02/29"`            |
    | 16 | `"year_week"`         | `"2000-W09"`            |
    | 17 | `"year_quarter"`      | `"2000-Q1"`             |

    The time styles are numerous and can handle localization to any supported locale. The following
    table provides a listing of all time styles and their output values (corresponding to an input
    time of `2000-02-29 14:35:00`).

    |    | Time Style    | Output                          | Notes         |
    |----|---------------|---------------------------------|---------------|
    | 1  | `"iso"`       | `"14:35:00"`                    | ISO 8601, 24h |
    | 2  | `"iso-short"` | `"14:35"`                       | ISO 8601, 24h |
    | 3  | `"h_m_s_p"`   | `"2:35:00 PM"`                  | 12h           |
    | 4  | `"h_m_p"`     | `"2:35 PM"`                     | 12h           |
    | 5  | `"h_p"`       | `"2 PM"`                        | 12h           |

    We can use the `info_date_style()` and `info_time_style()` functions within the console to view
    similar tables of date and time styles with example output.

    Returns
    -------
    GT
        The GT object is returned. This is the same object that the method is called on so that we
        can facilitate method chaining.

    Examples
    --------
    Let's use the `exibble` dataset to create a simple, two-column table (keeping only the `date`
    and `time` columns). With the `fmt_datetime()` method, we'll format the `date` column to display
    dates formatted with the `"month_day_year"` date style and the `time` column to display times
    formatted with the `"h_m_s_p"` time style.

    ```{python}
    from great_tables import GT, exibble

    exibble_mini = exibble[["date", "time"]]

    (
        GT(exibble_mini)
        .fmt_datetime(
            columns="date",
            date_style="month_day_year",
            time_style="h_m_s_p"
        )
    )
    ```
    """

    # Stop if `locale` does not have a valid value; normalize locale and resolve one
    # that might be set globally
    _validate_locale(locale=locale)
    locale = _normalize_locale(locale=locale)

    # Get the date format string based on the `date_style` value
    date_format_str = _get_date_format(date_style=date_style)

    # Get the time format string based on the `time_style` value
    time_format_str = _get_time_format(time_style=time_style)

    # Generate a function that will operate on single `x` values in the table body using both
    # the date and time format strings
    def fmt_datetime_fn(
        x: Any,
        date_format_str: str = date_format_str,
        time_format_str: str = time_format_str,
        sep: str = sep,
        locale: Union[str, None] = locale,
    ) -> str:
        # If the `x` value is a Pandas 'NA', then return the same value
        if pd.isna(x):
            return x

        # From the date and time format strings, create a datetime format string
        datetime_format_str = f"{date_format_str}'{sep}'{time_format_str}"

        # If `x` is a string, assume it is an ISO datetime string and convert it to a datetime object
        if isinstance(x, str):
            # Stop if `x` is not a valid ISO datetime string
            _validate_iso_datetime_str(x=x)

            # Ensure that a seconds value is present in the ISO datetime string
            x = _normalize_iso_datetime_str(x=x)

            # Convert the ISO datetime string to a datetime object
            x = _iso_to_datetime(x)

        else:
            # Stop if `x` is not a valid datetime object
            _validate_datetime_obj(x=x)

        # Fix up the locale for `format_datetime()` by replacing any hyphens with underscores
        if locale is None:
            locale = "en_US"
        else:
            locale = _str_replace(locale, "-", "_")

        # Format the datetime object to a string using Babel's `format_datetime()` function
        x_formatted = format_datetime(x, format=datetime_format_str, locale=locale)

        # Use a supplied pattern specification to decorate the formatted value
        if pattern != "{x}":
            x_formatted = pattern.replace("{x}", x_formatted)

        return x_formatted

    return fmt(self, fns=fmt_datetime_fn, columns=columns, rows=rows)


def _validate_iso_datetime_str(x: str) -> None:
    """
    Validate an ISO datetime string.

    Parameters
    ----------
    x
        The string to validate.

    Raises
    ------
    ValueError
        Raised if the string is not a valid ISO datetime string.
    """

    import re

    # Define the regex pattern for a valid ISO datetime string
    _ISO_DATETIME_REGEX = r"^\d{4}-\d{2}-\d{2}(T| )\d{2}:\d{2}(:\d{2})?$"

    # Use regex to determine if string is a valid ISO datetime string
    if not re.match(_ISO_DATETIME_REGEX, x):
        raise ValueError(f'"{x}" is not a valid ISO datetime string')

    return


def _normalize_iso_datetime_str(x: str) -> str:
    """
    Normalize an ISO datetime string.

    Parameters
    ----------
    x
        The string to normalize.

    Returns
    -------
    str
        The normalized string.
    """

    # If the string does not have a seconds value, then add one
    if len(x) == 16:
        x = x + ":00"

    return x


def fmt_markdown(
    self: GTSelf,
    columns: SelectExpr = None,
    rows: Union[int, List[int], None] = None,
) -> GTSelf:
    """
    Format Markdown text.

    Any Markdown-formatted text in the incoming cells will be transformed during render when using
    the `fmt_markdown()` method.

    Parameters
    ----------
    columns
        The columns to target. Can either be a single column name or a series of column names
        provided in a list.
    rows
        In conjunction with `columns=`, we can specify which of their rows should undergo
        formatting. The default is all rows, resulting in all rows in targeted columns being
        formatted. Alternatively, we can supply a list of row indices.

    Returns
    -------
    GT
        The GT object is returned. This is the same object that the method is called on so that we
        can facilitate method chaining.

    See Also
    --------
    The functional version of this method,
    [`val_fmt_markdown()`](`great_tables._formats_vals.val_fmt_markdown`), allows you to format a
    single string value (or a list of them).
    """

    # Generate a function that will operate on single `x` values in the table body
    def fmt_markdown_fn(x: Any) -> str:
        # If the `x` value is a Pandas 'NA', then return the same value
        if pd.isna(x):
            return x

        x_str: str = str(x)

        x_formatted = _md_html(x_str)

        return x_formatted

    return fmt(self, fns=fmt_markdown_fn, columns=columns, rows=rows)


def _value_to_decimal_notation(
    value: Union[int, float],
    decimals: int = 2,
    n_sigfig: Optional[int] = None,
    drop_trailing_zeros: bool = False,
    drop_trailing_dec_mark: bool = True,
    use_seps: bool = True,
    sep_mark: str = ",",
    dec_mark: str = ".",
    force_sign: bool = False,
) -> str:
    """
    Decimal notation.

    Returns a string value with the correct precision or fixed number of decimal places (with
    optional formatting of the decimal part).
    """

    is_positive = value > 0

    if n_sigfig:
        # If there is a value provided to `n_sigfig` then number formatting proceeds through the
        # significant digits pathway, which ignores `decimals` and any removal of trailing zero values
        # in the decimal portion of the value
        result = _format_number_n_sigfig(
            value=value,
            n_sigfig=n_sigfig,
            use_seps=use_seps,
            sep_mark=sep_mark,
            dec_mark=dec_mark,
            preserve_integer=False,
        )

    else:
        # If there is nothing provided to `n_sigfig` then the conventional decimal number formatting
        # pathway is taken; this formats to a specific number of decimal places and removal of
        # trailing zero values can be undertaken
        result = _format_number_fixed_decimals(
            value=value,
            decimals=decimals,
            drop_trailing_zeros=drop_trailing_zeros,
            use_seps=use_seps,
            sep_mark=sep_mark,
            dec_mark=dec_mark,
        )

    # Drop the trailing decimal mark if it is present
    if drop_trailing_dec_mark is True:
        result = result.rstrip(dec_mark)

    # Add in a trailing decimal mark under specific circumstances
    if drop_trailing_dec_mark is False and dec_mark not in result:
        result = result + dec_mark

    # Force the positive sign to be present if the `force_sign` option is taken
    if is_positive and force_sign:
        result = "+" + result

    return result


def _value_to_scientific_notation(
    value: Union[int, float],
    decimals: int = 2,
    n_sigfig: Optional[int] = None,
    dec_mark: str = ".",
) -> str:
    """
    Scientific notation.

    Returns a string value with the correct precision and 10s exponent. An 'E' is placed between
    the decimal value and 10s exponent.
    """

    # Transform value of `decimals` to `n_sigfig`
    if n_sigfig:
        pass
    else:
        n_sigfig = decimals + 1

    is_negative, sig_digits, dot_power, ten_power = _get_sci_parts(value, n_sigfig)

    result = (
        ("-" if is_negative else "")
        + _insert_decimal_mark(digits=sig_digits, power=dot_power, dec_mark=dec_mark)
        + "E"
        + str(ten_power)
    )

    return result


def _value_to_engineering_notation(value: Union[int, float], n_sigfig: int, exp_style: str) -> str:
    """
    Engineering notation.

    Returns a string value with the correct precision and an exponent that is divisible by three.
    The `exp_style` text is placed between the decimal value and the exponent.
    """

    is_negative, sig_digits, dot_power, ten_power = _get_sci_parts(value, n_sigfig)

    eng_power = int(3 * math.floor(ten_power / 3))
    eng_dot = dot_power + ten_power - eng_power

    result = (
        ("-" if is_negative else "")
        + _insert_decimal_mark(digits=sig_digits, power=eng_dot)
        + exp_style
        + str(eng_power)
    )

    return result


def _format_number_n_sigfig(
    value: Union[int, float],
    n_sigfig: int,
    use_seps: bool = True,
    sep_mark: str = ",",
    dec_mark: str = ".",
    preserve_integer: bool = False,
) -> str:
    sig_digits, power, is_negative = _get_number_profile(value, n_sigfig)

    formatted_value = ("-" if is_negative else "") + _insert_decimal_mark(
        digits=sig_digits, power=power, dec_mark="."
    )

    # Get integer and decimal parts
    # Split number at `.` and obtain the integer and decimal parts
    number_parts = formatted_value.split(".")
    integer_part = number_parts[0]
    decimal_part = number_parts[1] if len(number_parts) > 1 else ""

    # Initialize formatted representations of integer and decimal parts
    formatted_integer = ""
    formatted_decimal = dec_mark + decimal_part if decimal_part else ""

    if preserve_integer and "." not in formatted_value:
        formatted_value = "{:0.0f}".format(value)

    # Insert grouping separators within the integer part
    if use_seps:
        count = 0
        for digit in reversed(integer_part):
            if count and count % 3 == 0:
                formatted_integer = sep_mark + formatted_integer
            formatted_integer = digit + formatted_integer
            count += 1
    else:
        formatted_integer = integer_part

    # Combine the integer and decimal parts
    result = formatted_integer + formatted_decimal

    return result


def _format_number_fixed_decimals(
    value: Union[int, float],
    decimals: int,
    drop_trailing_zeros: bool = False,
    use_seps: bool = True,
    sep_mark: str = ",",
    dec_mark: str = ".",
) -> str:
    # If `number` is a string, cast it into a float
    if isinstance(value, str):
        value = float(value)

    is_negative = value < 0

    fmt_spec = f".{decimals}f"

    # Get the formatted `x` value
    value_str = format(value, fmt_spec)

    # Very small or very large numbers can be represented in exponential
    # notation but we don't want that; we need the string value to be fully
    # expanded with zeros so if an 'e' is detected we'll use a helper function
    # to ensure it's back to a number
    if "e" in value_str or "E" in value_str:
        value_str = _expand_exponential_to_full_string(str_number=value_str)

    # Split number at `.` and obtain the integer and decimal parts
    number_parts = value_str.split(".")
    integer_part = number_parts[0].lstrip("-")
    decimal_part = number_parts[1] if len(number_parts) > 1 else ""

    # Initialize formatted representations of integer and decimal parts
    formatted_integer = ""
    formatted_decimal = dec_mark + decimal_part if decimal_part else ""

    # Insert grouping separators within the integer part
    if use_seps:
        count = 0
        for digit in reversed(integer_part):
            if count and count % 3 == 0:
                formatted_integer = sep_mark + formatted_integer
            formatted_integer = digit + formatted_integer
            count += 1
    else:
        formatted_integer = integer_part

    # Add back the negative sign if the number is negative
    if is_negative:
        formatted_integer = "-" + formatted_integer

    # Combine the integer and decimal parts
    result = formatted_integer + formatted_decimal

    # Drop any trailing zeros if option is taken (this purposefully doesn't apply to numbers
    # formatted to a specific number of significant digits)
    if drop_trailing_zeros is True:
        result = result.rstrip("0")

    return result


def _format_number_compactly(
    value: Union[int, float],
    decimals: int,
    n_sigfig: Optional[int],
    drop_trailing_zeros: bool,
    drop_trailing_dec_mark: bool,
    use_seps: bool,
    sep_mark: str,
    dec_mark: str,
    force_sign: bool,
) -> str:
    # If the value is exactly zero, then we can return `0` immediately
    if value == 0:
        return "0"

    # Stop if `n_sigfig` does not have a valid value
    if n_sigfig is not None:
        _validate_n_sigfig(n_sigfig=n_sigfig)

    # Determine the power index for the value
    if value == 0:
        # If the value is zero, then the power index is 1; otherwise, we'd get
        # an error when trying to calculate the log of zero
        num_power_idx = 1
    else:
        # Determine the power index for the value and put it in the range of 0 to 5 which
        # corresponds to the list of suffixes `["", "K", "M", "B", "T", "Q"]`
        num_power_idx = math.floor(math.log(abs(value), 1000))
        num_power_idx = max(0, min(5, num_power_idx))

    # The `units_str` is obtained by indexing a list of suffixes with the `num_power_idx`
    units_str = ["", "K", "M", "B", "T", "Q"][num_power_idx]

    # Scale `x` value by a defined `base` value, this is done by dividing by the `base`
    # value (`1000`) raised to the power index
    value = value / 1000**num_power_idx

    # Format the value to decimal notation; this is done before the `byte_units` text
    # is affixed to the value
    x_formatted = _value_to_decimal_notation(
        value=value,
        decimals=decimals,
        n_sigfig=n_sigfig,
        drop_trailing_zeros=drop_trailing_zeros,
        drop_trailing_dec_mark=drop_trailing_dec_mark,
        use_seps=use_seps,
        sep_mark=sep_mark,
        dec_mark=dec_mark,
        force_sign=force_sign,
    )

    # Create a `suffix_pattern` object for affixing the `units_str`, which is the
    # string that represents the 'K', 'M', 'B', 'T', or 'Q' suffix
    suffix_pattern = f"{{x}}{units_str}"

    x_formatted = suffix_pattern.replace("{x}", x_formatted)

    return x_formatted


def _expand_exponential_to_full_string(str_number: str) -> str:
    decimal_number = Decimal(str_number)
    formatted_number = "{:f}".format(decimal_number)
    return formatted_number


def _get_number_profile(value: Union[int, float], n_sigfig: int) -> tuple[str, int, bool]:
    """
    Get key components of a number for decimal number formatting.

    Returns a tuple containing: (1) a string value of significant digits, (2) an
    exponent to get the decimal mark to the proper location, and (3) a boolean
    value that's True if the value is less than zero (i.e., negative).
    """
    value = float(value)
    is_negative = value < 0
    value = abs(value)

    if value == 0:
        sig_digits = str(("0" * n_sigfig))
        power = -(1 - n_sigfig)
    else:
        power = -1 * math.floor(math.log10(value)) + n_sigfig - 1
        value_power = value * 10.0**power

        if value < 1 and math.floor(math.log10(int(round(value_power)))) > math.floor(
            math.log10(int(value_power))
        ):
            power -= 1

        sig_digits = str(int(round(value * 10.0**power)))

    return sig_digits, int(-power), is_negative


def _get_sci_parts(value: Union[int, float], n_sigfig: int) -> tuple[bool, str, int, int]:
    """
    Returns the properties for constructing a number in scientific notation.
    """

    value = float(value)
    sig_digits, power, is_negative = _get_number_profile(value, n_sigfig)

    dot_power = -(n_sigfig - 1)
    ten_power = power + n_sigfig - 1

    return is_negative, sig_digits, dot_power, ten_power


def _insert_decimal_mark(digits: str, power: int, dec_mark: str = ".") -> str:
    """
    Places the decimal mark in the correct location within the digits.

    Should the decimal mark be outside the numeric range, zeros will be added.
    If `drop_trailing_zeros` is True, trailing decimal zeros will be removed.

    Examples:
      _insert_decimal_mark("123",   2, False) => "12300"
      _insert_decimal_mark("123",  -2, False) => "1.23"
      _insert_decimal_mark("123",   3, False) => "0.123"
      _insert_decimal_mark("123",   5, False) => "0.00123"
      _insert_decimal_mark("120",   0, False) => "120."
      _insert_decimal_mark("1200", -2, False) => "12.00"
      _insert_decimal_mark("1200", -2, True ) => "12"
      _insert_decimal_mark("1200", -1, False) => "120.0"
      _insert_decimal_mark("1200", -1, True ) => "120"
    """

    if power > 0:
        out = digits + "0" * power

    elif power < 0:
        power = abs(power)
        n_sigfig = len(digits)

        if power < n_sigfig:
            out = digits[:-power] + dec_mark + digits[-power:]

        else:
            out = "0" + dec_mark + "0" * (power - n_sigfig) + digits

    else:
        out = digits + (dec_mark if digits[-1] == "0" and len(digits) > 1 else "")

    return out


def _listify(
    x: Union[T, List[T], None],
    default: Callable[[], List[T]],
) -> List[T]:
    """
    Convert the input into a list.

    Parameters
    ----------
    x
        The input value to be converted into a list. It can be a single value of type T, a list of
        values of type T, or None.
    default
        A callable that returns a default list when the input value is None.

    Returns
    -------

    List[T]: The converted list.

    Raises:
        None

    Examples:
        _listify(5, lambda: [1, 2, 3])  # Output: [5]
        _listify([1, 2, 3], lambda: [4, 5, 6])  # Output: [1, 2, 3]
        _listify(None, lambda: ['a', 'b', 'c'])  # Output: ['a', 'b', 'c']
    """
    if x is None:
        return default()
    elif not isinstance(x, list):
        return [x]
    else:
        return cast(Any, x)


def _has_negative_value(value: Union[int, float]) -> bool:
    return value < 0


def _has_positive_value(value: Union[int, float]) -> bool:
    return value > 0


def _has_zero_value(value: Union[int, float]) -> bool:
    return value == 0


def _has_sci_order_zero(value: Union[int, float]) -> bool:
    return (value >= 1 and value < 10) or (value <= -1 and value > -10) or value == 0


def _context_exp_marks() -> List[str]:
    return [" \u00D7 10<sup style='font-size: 65%;'>", "</sup>"]


def _context_exp_str(exp_style: str) -> str:
    if exp_style == "low-ten":
        # For the 'low-ten' style, use a specialized `exp_str` string value
        exp_str = "<sub style='font-size: 65%;'>10</sub>"

    elif _str_detect(exp_style, "^[a-zA-Z]{1}1?$"):
        # If there is a single letter (or a letter and a '1') then
        # use that letter as the `exp_str` value
        exp_str = exp_style[0]

    else:
        # Use `E` if none of the above conditions are met
        exp_str = "E"

    return exp_str


def _context_minus_mark() -> str:
    return "\u2212"


def _replace_minus(string: str, minus_mark: str) -> str:
    """
    Replaces all occurrences of the minus sign '-' in the given string with the specified minus mark.

    Args:
        string (str): The input string.
        minus_mark (str): The mark to replace the minus sign with.

    Returns:
        str: The modified string with the minus sign replaced.
    """
    return _str_replace(string, "-", minus_mark)


def _filter_pd_df_to_row(pd_df: pd.DataFrame, column: str, filter_expr: str) -> pd.DataFrame:
    filtered_pd_df = pd_df[pd_df[column] == filter_expr]
    if len(filtered_pd_df) != 1:
        raise Exception(
            "Internal Error, the filtered table doesn't result in a table of exactly one row."
        )
    return filtered_pd_df


def _get_locale_sep_mark(default: str, use_seps: bool, locale: Union[str, None] = None) -> str:
    # If `use_seps` is False, then force `sep_mark` to be an empty string
    if not use_seps:
        return ""

    # If `locale` is NULL then return the default `sep_mark`
    if locale is None:
        return default

    # Get the correct `group` value from the locales lookup table
    pd_df_row = _filter_pd_df_to_row(pd_df=_get_locales_data(), column="locale", filter_expr=locale)

    # Obtain a single cell value from the single row in `pd_df_row` that is below
    # the column named 'group'; this could potentially be of any type but we expect
    # it to be a string (and we'll check for that here)
    sep_mark: Any
    sep_mark = pd_df_row.iloc[0]["group"]
    if not isinstance(sep_mark, str):
        raise TypeError(f"Variable type mismatch. Expected str, got {type(sep_mark)}.")

    # Replace any `""` or "\u00a0" with `" "` since an empty string actually
    # signifies a space character, and, we want to normalize to a simple space
    sep_mark = " " if sep_mark == "" or sep_mark == "\u00a0" else sep_mark

    return sep_mark


def _get_locale_dec_mark(default: str, locale: Union[str, None] = None) -> str:
    # If `locale` is NULL then return the default `dec_mark`
    if locale is None:
        return default

    # Get the correct `decimal` value row from the locales lookup table
    pd_df_row = _filter_pd_df_to_row(pd_df=_get_locales_data(), column="locale", filter_expr=locale)

    # Obtain a single cell value from the single row in `pd_df_row` that is below
    # the column named 'decimal'; this could potentially be of any type but we expect
    # it to be a string (and we'll check for that here)
    dec_mark: Any
    dec_mark = pd_df_row.iloc[0]["decimal"]
    if not isinstance(dec_mark, str):
        raise TypeError(f"Variable type mismatch. Expected str, got {type(dec_mark)}.")

    return dec_mark


def _get_locales_list() -> List[str]:
    """
    Returns a list of locales as strings.

    Raises:
        TypeError: If the first element of the locale list is not a string.
    """

    # Get the 'locales' dataset and obtain from that a list of locales
    locales = _get_locales_data()
    locale_list = locales["locale"].tolist()

    # Ensure that `locale_list` is of the type 'str'
    locale_list: Any
    if not isinstance(locale_list[0], str):
        raise TypeError("Variable type mismatch. Expected str, got something entirely different.")
    return locale_list


def _get_default_locales_list() -> List[str]:
    """
    Returns a list of default locales.

    The function retrieves the default locales data and extracts the default locale list.
    It ensures that the list is of type 'str' and raises a TypeError if not.

    Returns:
        A list of default locales as strings.
    """

    # Get the 'default locales' dataset and obtain from that a list of default locales
    default_locales = _get_default_locales_data()
    default_locale_list = default_locales["default_locale"].tolist()

    # Ensure that `default_locale_list` is of the type 'str'
    default_locale_list: Any
    if not isinstance(default_locale_list[0], str):
        raise TypeError("Variable type mismatch. Expected str, got something entirely different.")

    return default_locale_list


def _validate_locale(locale: Union[str, None] = None) -> None:
    """
    Validates the given locale string against a list of supported locales.

    Args:
        locale (str or None): The locale string to validate. If None, the function returns without
        doing anything.

    Raises:
        ValueError: If the supplied `locale` is not available in the list of supported locales.
    """

    # If `locale` is None then return without doing anything (nothing to validate)
    if locale is None:
        return

    locales_list = _get_locales_list()
    default_locales_list = _get_default_locales_list()

    # Replace any underscores with hyphens
    supplied_locale = _str_replace(locale, "_", "-")

    # Stop if the `locale` provided isn't a valid one
    if supplied_locale not in locales_list and supplied_locale not in default_locales_list:
        raise ValueError("The supplied `locale` is not available in the list of supported locales.")

    return


def _normalize_locale(locale: Union[str, None] = None) -> Union[str, None]:
    """
    Normalize the given locale string by replacing any underscores with hyphens and resolving any default locales into their base names.

    Args:
        locale (str or None): The locale string to normalize. If None, returns None.

    Returns:
        str or None: The normalized locale string, or None if the input was None.

    Raises:
        TypeError: If the resolved locale is not of type 'str'.
    """

    # If `locale` is None then return None (we don't need to normalize anything here)
    if locale is None:
        return None

    # Replace any underscores with hyphens
    supplied_locale = _str_replace(locale, "_", "-")

    # Resolve any default locales into their base names (e.g., 'en-US' -> 'en')
    if supplied_locale in _get_default_locales_list():
        default_locales = _get_default_locales_data()
        resolved_locale = default_locales[
            default_locales["default_locale"] == supplied_locale
        ].iloc[0]["base_locale"]

        # Ensure that `resolved_locale` is of the type 'str'
        resolved_locale: Any
        if not isinstance(resolved_locale, str):
            raise TypeError(
                "Variable type mismatch. Expected str, got something entirely different."
            )
    else:
        resolved_locale = supplied_locale

    return resolved_locale


def _resolve_locale(x: GTData, locale: Union[str, None] = None) -> Union[str, None]:
    # Get the locale from the locale value set globally; note that this may also be None
    # but a None value will eventually be resolved to the 'en' locale
    locale = x._locale._locale if locale is None else locale

    # An 'undetermined' locale should map back to the 'en' locale
    if locale == "und":
        locale = "en"

    locale = _normalize_locale(locale=locale)

    _validate_locale(locale=locale)

    return locale


def _get_locale_currency_code(locale: Union[str, None] = None) -> str:
    """
    Given a locale, returns the corresponding currency code. If no locale is provided,
    returns the currency code for the United States ('USD').

    Args:
        locale (str or None): A string representing the locale for which to retrieve the
            currency code. If None, the currency code for the United States ('USD') is returned.

    Returns:
        str: A string representing the currency code for the specified locale.

    Raises:
        TypeError: If the currency code is not a string.

    """

    # If `locale` is None then return `"USD"`
    if locale is None:
        return "USD"

    # Get the correct 'locale' value row from the `__x_locales` lookup table
    pd_df_row = _filter_pd_df_to_row(pd_df=_get_locales_data(), column="locale", filter_expr=locale)

    # Extract the 'currency_code' cell value from this 1-row DataFrame
    currency_code = pd_df_row.iloc[0]["currency_code"]

    # Ensure that `currency_code` is of the type 'str'
    currency_code: Any
    if not isinstance(currency_code, str):
        raise TypeError("Variable type mismatch. Expected str, got something entirely different.")

    # If the field isn't populated, we'll obtain an empty string; in such a case we fall
    # back to using the 'USD' currency code
    if currency_code == "":
        currency_code = "USD"

    return currency_code


def _get_currency_str(currency: str) -> str:
    """
    Given a currency code, returns the corresponding currency symbol as a string.

    Args:
        currency (str): The currency code to look up.

    Returns:
        str: The currency symbol corresponding to the given currency code.

    Raises:
        TypeError: If the currency symbol is not of type 'str'.
    """

    # Get the correct 'curr_code' value row from the `__x_currencies` lookup table
    pd_df_row = _filter_pd_df_to_row(
        pd_df=_get_currencies_data(), column="curr_code", filter_expr=currency
    )

    # Extract the 'symbol' cell value from this 1-row DataFrame
    currency_str = pd_df_row.iloc[0]["symbol"]

    # Ensure that `currency_str` is of the type 'str'
    currency_str: Any
    if not isinstance(currency_str, str):
        raise TypeError("Variable type mismatch. Expected str, got something entirely different.")

    return currency_str


def _validate_currency(currency: str) -> None:
    """
    Validates if the provided currency is available in the list of supported currencies.

    Args:
    - currency (str): The currency code to validate

    Raises:
    - ValueError: If the `currency` provided isn't a valid one

    Returns:
    - None
    """

    # Get the currencies data
    currencies = _get_currencies_data()

    # Get the `curr_code` column from currencies DataFrame as a list
    curr_code_list: List[str] = currencies["curr_code"].tolist()

    # Stop if the `currency` provided isn't a valid one
    if currency not in curr_code_list:
        raise ValueError(
            "The supplied `currency` is not available in the list of supported currencies."
        )

    return


def _get_currency_decimals(currency: str, decimals: Optional[int], use_subunits: bool) -> int:
    """
    Returns the number of decimal places to use for a given currency.

    If `decimals` is not None, it is returned. Otherwise, if `use_subunits` is True,
    the number of decimal places is determined by the currency's exponent. Otherwise,
    the number of decimal places is 0.

    Args:
        currency (str): The currency code.
        decimals (Optional[int]): The number of decimal places to use, if specified.
        use_subunits (bool): Whether to use subunits for the currency.

    Returns:
        int: The number of decimal places to use.
    """

    # If `decimals` is not None, return it
    if decimals is not None:
        return decimals

    # If `decimals` is None, then we need to determine the number of decimal places
    if decimals is None and use_subunits:
        # Get the number of decimal places from the currency's exponent
        decimals = _get_currency_exponent(currency=currency)
    elif decimals is None and not use_subunits:
        # If `use_subunits` is False, then the number of decimal places is 0
        decimals = 0

    # Assert that `decimals` is not None and then return it
    assert decimals is not None
    return decimals


def _get_currency_exponent(currency: str) -> int:
    """
    Given a currency code, returns the exponent associated with that` currency.
    If the currency code is not found, returns 2 as a default value.

    Args:
        currency (str): The currency code to look up.

    Returns:
        int: The exponent associated with the currency code.
    """
    currencies = _get_currencies_data()

    # get the curr_code column from currencies df as a list
    curr_code_list: List[str] = currencies["curr_code"].tolist()

    if currency in curr_code_list:
        exponent = currencies[currencies["curr_code"] == currency].iloc[0]["exponent"]

        # Cast exponent variable as an integer value (it is a str currently)
        exponent = int(exponent)

        # Ensure that `exponent` is of the type 'int'
        exponent: Any
        if not isinstance(exponent, int):
            raise TypeError(
                "Variable type mismatch. Expected int, got something entirely different."
            )
    else:
        exponent = 2

    return exponent


def _validate_n_sigfig(n_sigfig: int) -> None:
    """
    Validates the input for the number of significant figures.

    Args:
        n_sigfig (int): The number of significant figures to validate.

    Raises:
        ValueError: If the length of `n_sigfig` is not 1, or if the value is `None` or less than 1.
        TypeError: If the input for `n_sigfig` is not an integer.

    Returns:
        None
    """

    # Check that the input `n_sigfig` is a scalar value (not a list or tuple)
    if isinstance(n_sigfig, (list, tuple)):
        raise TypeError("Any input for `n_sigfig` must be a scalar value.")
    # Check that the input `n_sigfig` is not `None`
    if not isinstance(n_sigfig, int):
        raise TypeError("Any input for `n_sigfig` must be an integer.")
    # The value of `n_sigfig` must be greater than or equal to 1
    if n_sigfig < 1:
        raise ValueError("The value for `n_sigfig` must be greater than or equal to `1`.")

    return


def _round_rhu(x: Union[float, int], digits: int = 0) -> float:
    """
    Rounds a number using the 'Round-Half-Up' (R-H-U) algorithm.

    Args:
        x (float): The number to round.
        digits (int): The number of digits to round to.

    Returns:
        float: The rounded number.
    """

    # Multiply the number by 10^digits to move the decimal point to the right
    z = x * 10**digits

    # Add 0.5 + 2.220446049250313e-16 to the number to ensure that the number is rounded up
    z += 0.5 + math.sqrt(2.220446049250313e-16)

    # Truncate the number to remove the decimal places
    z = math.trunc(z)

    # Divide the number by 10^digits to move the decimal point back to the original position
    z /= 10**digits

    return z


def _as_roman(x: int) -> str:
    """
    Converts an integer to a Roman numeral string.

    Args:
        x (int): The integer to convert.

    Returns:
        str: The Roman numeral string representation of the integer.
    """

    roman_key_value_list = [
        (1000, "M"),
        (900, "CM"),
        (500, "D"),
        (400, "CD"),
        (100, "C"),
        (90, "XC"),
        (50, "L"),
        (40, "XL"),
        (10, "X"),
        (9, "IX"),
        (5, "V"),
        (4, "IV"),
        (1, "I"),
    ]

    out = ""
    while x > 0:
        for i, r in roman_key_value_list:
            while x >= i:
                out += r
                x -= i
    return out


def _validate_case(case: str) -> None:
    """
    Validates the case argument for the `fmt_roman()` method.

    Args:
        case (str): The case argument to validate.

    Raises:
        ValueError: If the case argument is not 'upper' or 'lower'.
    """
    if case not in ["upper", "lower"]:
        raise ValueError(f"The `case` argument must be either 'upper' or 'lower' (not '{case}').")

    return


def _get_date_formats_dict() -> Dict[str, str]:
    date_formats = {
        "iso": "y-MM-dd",
        "wday_month_day_year": "EEEE, MMMM d, y",
        "wd_m_day_year": "EEE, MMM d, y",
        "wday_day_month_year": "EEEE d MMMM y",
        "month_day_year": "MMMM d, y",
        "m_day_year": "MMM d, y",
        "day_m_year": "d MMM y",
        "day_month_year": "d MMMM y",
        "day_month": "d MMMM",
        "day_m": "d MMM",
        "year": "y",
        "month": "MMMM",
        "day": "dd",
        "year.mn.day": "y/MM/dd",
        "y.mn.day": "yy/MM/dd",
        "year_week": "y-'W'ww",
        "year_quarter": "y-'Q'Q",
    }

    return date_formats


def _get_time_formats_dict() -> Dict[str, str]:
    time_formats = {
        "iso": "HH:mm:ss",
        "iso-short": "HH:mm",
        "h_m_s_p": "h:mm:ss a",
        "h_m_p": "h:mm a",
        "h_p": "h a",
    }

    return time_formats


def _get_date_format(date_style: str) -> str:
    """
    Get the date format string based on the date style.

    Args:
        date_style (str): The style of the date.

    Returns:
        str: The date format string.

    Raises:
        ValueError: If `date_style` does not have a valid value.
    """
    date_formats = _get_date_formats_dict()

    # Stop if `date_style` does not have a valid value
    _validate_date_style(date_style=date_style)

    # Get the date format string based on the date style
    date_format_str = date_formats[date_style]

    return date_format_str


def _get_time_format(time_style: str) -> str:
    """
    Get the time format string based on the given time style.

    Args:
        time_style (str): The style of the time format.

    Returns:
        str: The time format string.

    Raises:
        ValueError: If `time_style` does not have a valid value.
    """
    time_formats = _get_time_formats_dict()

    # Stop if `time_style` does not have a valid value
    _validate_time_style(time_style=time_style)

    # Get the time format string based on the date style
    time_format_str = time_formats[time_style]

    return time_format_str


def _validate_date_style(date_style: str) -> None:
    """
    Validates the given date style.

    Args:
        date_style (str): The date style to be validated.

    Raises:
        ValueError: If `date_style` is not a valid value.

    Returns:
        None
    """
    if date_style not in _get_date_formats_dict():
        raise ValueError(f"date_style must be one of: {', '.join(_get_date_formats_dict().keys())}")

    return


def _validate_time_style(time_style: str) -> None:
    """
    Validate the time style.

    Args:
        time_style (str): The time style to validate.

    Raises:
        ValueError: If `time_style` is not a valid value.

    Returns:
        None
    """
    if time_style not in _get_time_formats_dict():
        raise ValueError(f"time_style must be one of: {', '.join(_get_time_formats_dict().keys())}")

    return


def _iso_to_date(x: str) -> date:
    """
    Converts a string in ISO format (YYYY-MM-DD) to a date object.

    Args:
        x (str): The string to be converted.

    Returns:
        date: The converted date object.
    """
    return datetime.strptime(x, "%Y-%m-%d").date()


def _iso_to_time(x: str) -> time:
    """
    Converts a string in ISO format to a time object.

    Args:
        x (str): The string to be converted.

    Returns:
        time: The converted time object.
    """
    return datetime.strptime(x, "%H:%M:%S").time()


def _iso_to_datetime(x: str) -> datetime:
    """
    Converts a string in ISO format to a datetime object.

    Args:
        x (str): The string to be converted.

    Returns:
        datetime: The converted datetime object.
    """
    return datetime.strptime(x, "%Y-%m-%d %H:%M:%S")


def _validate_iso_date_str(x: str) -> None:
    """
    Validates if the given string is a valid ISO date string in the format 'YYYY-MM-DD'.

    Args:
        x (str): The string to be validated.

    Raises:
        ValueError: If the string is not a valid ISO date string.

    Returns:
        None
    """
    try:
        datetime.strptime(x, "%Y-%m-%d")
    except ValueError:
        raise ValueError(
            f"Invalid ISO date string: '{x}'. The string must be in the format 'YYYY-MM-DD'."
        )

    return


def _validate_iso_time_str(x: str) -> None:
    """
    Validates if the input string `x` is a valid ISO time string.

    Args:
        x (str): The input string to be validated.

    Raises:
        ValueError: If `x` is not a valid ISO time string (HH:MM:SS or HH:MM).

    Returns:
        None
    """
    try:
        datetime.strptime(x, "%H:%M:%S")
    except ValueError:
        try:
            datetime.strptime(x, "%H:%M")
        except ValueError:
            raise ValueError(
                f"Invalid ISO time string: '{x}'."
                " The string must be in the format 'HH:MM:SS' or 'HH:MM'."
            )

    return


def _normalize_iso_time_str(x: str) -> str:
    """
    Normalize the input ISO time string by expanding it to include the seconds component if necessary.

    Args:
        x (str): The input ISO time string.

    Returns:
        str: The normalized ISO time string.
    """
    if len(x) == 5:
        x = x + ":00"

    return x


def _validate_date_obj(x: Any) -> None:
    """
    Validate if the given object is a valid date object.

    Args:
        x (Any): The object to be validated.

    Raises:
        ValueError: If the object is not a valid date object.

    Returns:
        None
    """
    if not isinstance(x, date):
        raise ValueError(f"Invalid date object: '{x}'. The object must be a date object.")

    return


def _validate_time_obj(x: Any) -> None:
    """
    Validate if the given object is a valid time object.

    Args:
        x (Any): The object to be validated.

    Raises:
        ValueError: If the object is not a valid time object.

    Returns:
        None
    """
    if not isinstance(x, time):
        raise ValueError(f"Invalid time object: '{x}'. The object must be a time object.")

    return


def _validate_datetime_obj(x: Any) -> None:
    """
    Validate if the given object is a valid datetime object.

    Args:
        x (Any): The object to be validated.

    Raises:
        ValueError: If the object is not a valid datetime object.

    Returns:
        None
    """
    if not isinstance(x, datetime):
        raise ValueError(f"Invalid datetime object: '{x}'. The object must be a datetime object.")

    return


def fmt_image(
    self: GTSelf,
    columns: SelectExpr = None,
    rows: Union[int, List[int], None] = None,
    height: str | int | None = None,
    width: str | int | None = None,
    sep: str = " ",
    path: str | Path | None = None,
    file_pattern: str = "{}",
    encode: bool = True,
) -> GTSelf:
    """Format image paths to generate images in cells.

    To more easily insert graphics into body cells, we can use the `fmt_image()` method. This allows
    for one or more images to be placed in the targeted cells. The cells need to contain some
    reference to an image file, either: (1) complete http/https or local paths to the files; (2) the
    file names, where a common path can be provided via `path=`; or (3) a fragment of the file name,
    where the `file_pattern=` argument helps to compose the entire file name and `path=` provides
    the path information. This should be expressly used on columns that contain *only* references to
    image files (i.e., no image references as part of a larger block of text). Multiple images can
    be included per cell by separating image references by commas. The `sep=` argument allows for a
    common separator to be applied between images.

    Parameters
    ----------
    columns
        The columns to target. Can either be a single column name or a series of column names
        provided in a list.
    rows
        In conjunction with `columns=`, we can specify which of their rows should undergo
        formatting. The default is all rows, resulting in all rows in targeted columns being
        formatted. Alternatively, we can supply a list of row indices.
    height
        The height of the rendered images.
    width
        The width of the rendered images.
    sep
        In the output of images within a body cell, `sep=` provides the separator between each
        image.
    path
        An optional path to local image files (this is combined with all filenames).
    file_pattern
        The pattern to use for mapping input values in the body cells to the names of the graphics
        files. The string supplied should use `"{}"` in the pattern to map filename fragments to
        input strings.
    encode
        The option to always use Base64 encoding for image paths that are determined to be local. By
        default, this is `True`.

    Examples
    --------
    Using a small portion of [`metro`] dataset, let's create a **gt** table. We will only include a
    few columns and rows from that table. The `lines` column has comma-separated listings of numbers
    corresponding to lines served at each station. We have a directory of SVG graphics for all of
    these lines in the package (the path for the image directory can be accessed via
    `files("great_tables") / "data/metro_images"`, using the `importlib_resources` package). The
    filenames roughly corresponds to the data in the `lines` column. The `fmt_image()` function can
    be used with these inputs since the `path=` and `file_pattern=` arguments allow us to compose
    complete and valid file locations. What you get from this are sequences of images in the table
    cells, taken from the referenced graphics files on disk.

    ```{python}
    from great_tables import GT
    from great_tables.data import metro
    from importlib_resources import files

    img_paths = files("great_tables") / "data/metro_images"

    metro_mini = metro[["name", "lines", "passengers"]].head(5)

    (
        GT(metro_mini)
        .fmt_image(
            columns="lines",
            path=img_paths,
            file_pattern="metro_{}.svg"
        )
        .fmt_integer(columns="passengers")
    )
    ```
    """

    # TODO: most parameter options should allow a polars expression (or from_column) ----
    # can other fmt functions do this kind of thing?
    expr_cols = [height, width, sep, path, file_pattern, encode]

    if any(isinstance(x, PlExpr) for x in expr_cols):
        raise NotImplementedError(
            "fmt_image currently does not support polars expressions for arguments other than"
            " columns and rows"
        )

    if height is None and width is None:
        height = "2em"

    formatter = FmtImage(height, width, sep, str(path), file_pattern, encode)
    return fmt(self, fns=formatter.to_html, columns=columns, rows=rows)


from dataclasses import dataclass


@dataclass
class FmtImage:
    height: str | int | None = None
    width: str | None = None
    sep: str = " "
    path: str | None = None
    file_pattern: str = "{}"
    encode: bool = True

    SPAN_TEMPLATE: ClassVar = '<span style="white-space:nowrap;">{}</span>'

    def to_html(self, val: Any):
        import re
        from pathlib import Path

        # TODO: handle NA values
        # TODO: are we assuming val is a string? (or coercing?)

        # otherwise...

        if "," in val:
            files = re.split(r",\s*", val)
        else:
            files = [val]

        # TODO: if we allowing height and width to be set based on column values, then
        # they could end up as bespoke types like np int64, etc..
        # We should ensure we process those before hitting FmtImage
        if isinstance(self.height, (int, float)):
            height = f"{self.height}px"
        else:
            height = self.height

        # TODO: note that only height can be numeric in the R program. Is this on purpose?
        # In any event, raising explicitly for numeric width below.
        if isinstance(self.width, (int, float)):
            raise NotImplementedError("The width argument must be specified as a string.")

        full_files = self._apply_pattern(self.file_pattern, files)

        out: list[str] = []
        for file in full_files:
            # Case 1: from url
            if self.path and (self.path.startswith("http://") or self.path.startswith("https://")):
                norm_path = re.sub(r"/\s+$", self.path)
                uri = f"{norm_path}/{file}"

            # Case 2:
            else:
                filename = (Path(self.path or "") / file).expanduser().absolute()

                if self.encode:
                    uri = self._get_image_uri(filename)
                else:
                    uri = filename

            # TODO: do we have a way to create tags, that is good at escaping, etc..?
            out.append(self._build_img_tag(uri, height, self.width))

        img_tags = self.sep.join(out)
        span = self.SPAN_TEMPLATE.format(img_tags)

        return span

    @staticmethod
    def _apply_pattern(file_pattern: str, files: list[str]) -> list[str]:
        return [file_pattern.format(file) for file in files]

    @classmethod
    def _get_image_uri(cls, filename: str) -> str:
        import base64

        with open(filename, "rb") as f:
            encoded = base64.b64encode(f.read()).decode()

        mime_type = cls._get_mime_type(filename)

        return f"data: {mime_type}; base64,{encoded}"
        ...

    @staticmethod
    def _get_mime_type(filename: str) -> str:
        from pathlib import Path

        # note that we strip off the leading "."
        suffix = Path(filename).suffix[1:]

        if suffix == "svg":
            return "image/svg+xml"
        elif suffix == "jpg":
            return "image/jpeg"

        return f"image/{suffix}"

    @staticmethod
    def _build_img_tag(uri: str, height: str | None = None, width: str | None = None) -> str:
        style_string = "".join(
            [
                f"height: {height};" if height is not None else "",
                f"width: {width};" if width is not None else "",
                "vertical-align: middle;",
            ]
        )

        return f'<img src="{uri}" style="{style_string}">'


def fmt_nanoplot(
    self: GTSelf,
    columns: SelectExpr = None,
    rows: Union[int, List[int], None] = None,
    plot_type: PlotType = "line",
    plot_height: str = "2em",
    missing_vals: MissingVals = "marker",
    autoscale: bool = False,
    reference_line: Optional[Union[str, int, float]] = None,
    reference_area: Optional[List[Any]] = None,
    expand_x: Optional[Union[List[Union[int, float]], List[int], List[float]]] = None,
    expand_y: Optional[Union[List[Union[int, float]], List[int], List[float]]] = None,
    options: Optional[Dict[str, Any]] = None,
) -> GTSelf:
    """Format data for nanoplot visualizations.

    The `fmt_nanoplot()` method is used to format data for nanoplot visualizations. This method
    allows for the creation of a variety of different plot types, including line, bar, and scatter
    plots.

    :::{.callout-warning}
    `fmt_nanoplot()` is still experimental.
    :::

    Parameters
    ----------
    columns
        The columns to target. Can either be a single column name or a series of column names
        provided in a list.
    rows
        In conjunction with `columns=`, we can specify which of their rows should undergo
        formatting. The default is all rows, resulting in all rows in targeted columns being
        formatted. Alternatively, we can supply a list of row indices.
    plot_type
        Nanoplots can either take the form of a line plot (using `"line"`) or a bar plot (with
        `"bar"`). A line plot, by default, contains layers for a data line, data points, and a data
        area. With a bar plot, the always visible layer is that of the data bars.
    plot_height
        The height of the nanoplots. The default here is a sensible value of `"2em"`.
    missing_vals
        If missing values are encountered within the input data, there are three strategies
        available for their handling: (1) `"gap"` will show data gaps at the sites of missing data,
        where data lines will have discontinuities and bar plots will have missing bars; (2)
        `"marker"` will behave like `"gap"` but show prominent visual marks at the missing data
        locations; (3) `"zero"` will replace missing values with zero values; and (4) `"remove"`
        will remove any incoming missing values.
    autoscale
        Using `autoscale=True` will ensure that the bounds of all nanoplots produced are based on
        the limits of data combined from all input rows. This will result in a shared scale across
        all of the nanoplots (for *y*- and *x*-axis data), which is useful in those cases where the
        nanoplot data should be compared across rows.
    reference_line
        A reference line requires a single input to define the line. It could be a numeric value,
        applied to all nanoplots generated. Or, the input can be one of the following for generating
        the line from the underlying data: (1) `"mean"`, (2) `"median"`, (3) `"min"`, (4) `"max"`,
        (5) `"q1"`, (6) `"q3"`, (7) `"first"`, or (8) `"last"`.
    reference_area
        A reference area requires a list of two values for defining bottom and top boundaries (in
        the *y* direction) for a rectangular area. The types of values supplied are the same as
        those expected for `reference_line=`, which is either a numeric value or one of the
        following keywords for the generation of the value: (1) `"mean"`, (2) `"median"`, (3)
        `"min"`, (4) `"max"`, (5) `"q1"`, (6) `"q3"`, (7) `"first"`, or (8) `"last"`. Input can
        either be a vector or list with two elements.
    expand_x
        Should you need to have plots expand in the *x* direction, provide one or more values to
        `expand_x=`. Any values provided that are outside of the range of *x*-value data provided to
        the plot will result in a *x*-scale expansion.
    expand_y
        Similar to `expand_x=`, one can have plots expand in the *y* direction. To make this happen,
        provide one or more values to `expand_y=`. If any of the provided values are outside of the
        range of *y*-value data provided, the plot will result in a *y*-scale expansion.
    options
        By using the [`nanoplot_options()`](`great_tables.nanoplot_options`) helper function here,
        you can alter the layout and styling of the nanoplots in the new column.

    Details
    -------
    Nanoplots try to show individual data with reasonably good visibility. Interactivity is included
    as a basic feature so one can hover over the data points and vertical guides will display the
    value ascribed to each data point. Because **Great Tables** knows all about numeric formatting,
    values will be compactly formatted so as to not take up valuable real estate.

    While basic customization options are present in `fmt_nanoplot()`, many more opportunities for
    customizing nanoplots on a more granular level are possible with the aforementioned
    [`nanoplot_options()`](`great_tables.nanoplot_options`) helper function. With that, layers of
    the nanoplots can be selectively removed and the aesthetics of the remaining plot components can
    be modified.

    Examples
    --------
    Let's create a nanoplot from a Polars DataFrame containing multiple numbers per cell. The
    numbers are represented here as strings, where spaces separate the values, and the same values
    are present in two columns: `lines` and `bars`. We will use the `fmt_nanoplot()` method twice
    to create a line plot and a bar plot from the data in their respective columns.

    ```{python}
    from great_tables import GT
    import polars as pl

    random_numbers_df = pl.DataFrame(
        {
            "i": range(1, 5),
            "lines": [
                "20 23 6 7 37 23 21 4 7 16",
                "2.3 6.8 9.2 2.42 3.5 12.1 5.3 3.6 7.2 3.74",
                "-12 -5 6 3.7 0 8 -7.4",
                "2 0 15 7 8 10 1 24 17 13 6",
            ],
        }
    ).with_columns(bars=pl.col("lines"))

    (
        GT(random_numbers_df, rowname_col="i")
        .fmt_nanoplot(columns="lines")
        .fmt_nanoplot(columns="bars", plot_type="bar")
    )
    ```

    We can always represent the input DataFrame in a different way (with list columns) and
    `fmt_nanoplot()` will still work. While the input data is the same as in the previous example,
    we'll take the opportunity here to add a reference line and a reference area to the line plot
    and also to the bar plot.

    ```{python}
    random_numbers_df = pl.DataFrame(
        {
            "i": range(1, 5),
            "lines": [
                { "val": [20.0, 23.0, 6.0, 7.0, 37.0, 23.0, 21.0, 4.0, 7.0, 16.0] },
                { "val": [2.3, 6.8, 9.2, 2.42, 3.5, 12.1, 5.3, 3.6, 7.2, 3.74] },
                { "val": [-12.0, -5.0, 6.0, 3.7, 0.0, 8.0, -7.4] },
                { "val": [2.0, 0.0, 15.0, 7.0, 8.0, 10.0, 1.0, 24.0, 17.0, 13.0, 6.0] },
            ],
        }
    ).with_columns(bars=pl.col("lines"))

    (
        GT(random_numbers_df, rowname_col="i")
        .fmt_nanoplot(
            columns="lines",
            reference_line="mean",
            reference_area=["min", "q1"]
        )
        .fmt_nanoplot(
            columns="bars",
            plot_type="bar",
            reference_line="max",
            reference_area=["max", "median"])
    )
    ```

    Single-value bar plots and line plots can be made with `fmt_nanoplot()`. These run in the
    horizontal direction, which is ideal for tabular presentation. The key thing here is that
    `fmt_nanoplot()` expects a column of numeric values. These plots are meant for comparison
    across rows so the method automatically scales the horizontal bars to facilitate this type of
    display. The following example shows how `fmt_nanoplot()` can be used to create single-value bar
    and line plots.

    ```{python}
    single_vals_df = pl.DataFrame(
        {
            "i": range(1, 6),
            "bars": [4.1, 1.3, -5.3, 0, 8.2],
            "lines": [12.44, 6.34, 5.2, -8.2, 9.23]
        }
    )
    (
        GT(single_vals_df, rowname_col="i")
        .fmt_nanoplot(columns="bars", plot_type="bar")
        .fmt_nanoplot(columns="lines", plot_type="line")
    )
    ```
    """

    from great_tables._utils import _str_detect

    # Get the internal data table
    data_tbl = self._tbl_data

    column_d_type = data_tbl[columns].dtype

    col_class = str(column_d_type).lower()

    if _str_detect(col_class, "int") or _str_detect(col_class, "float"):
        scalar_vals = True
    else:
        scalar_vals = False

    # If a bar plot is requested and the data consists of single y values, then we need to
    # obtain a list of all single y values in the targeted column (from `columns`)
    if plot_type in ["line", "bar"] and scalar_vals:

        # Check each cell in the column and get each of them that contains a scalar value
        # Why are we grabbing the first element of a tuple? (Note this also happens again below.)
        all_single_y_vals = list(
            data_tbl[columns].apply(
                lambda x: x if pd.isna(x) else x[1] if isinstance(x, tuple) else x
            )
        )

        autoscale = False

    else:
        all_single_y_vals = None

    if options is None:
        from great_tables._helpers import nanoplot_options

        options_plots = nanoplot_options()
    else:
        options_plots = options

    # For autoscale, we need to get the minimum and maximum from all values for the y-axis
    if autoscale:

        from great_tables._utils_nanoplots import _flatten_list

        # TODO: if a column of delimiter separated strings is passed. E.g. "1 2 3 4". Does this mean
        # that autoscale does not work? In this case, is col_i_y_vals_raw a string that gets processed?
        # downstream?
        all_y_vals_raw = list(
            data_tbl[columns].apply(
                lambda x: x if pd.isna(x) else x[1] if isinstance(x, tuple) else x
            )
        )

        all_y_vals = []

        for i, data_vals_i in enumerate(all_y_vals_raw):
            # TODO: this dictionary handling seems redundant with _generate_data_vals dict handling?
            # Can this if-clause be removed?
            if isinstance(data_vals_i, dict):

                if len(data_vals_i) == 1:
                    # If there is only one key in the dictionary, then we can assume that the
                    # dictionary deals with y-values only
                    data_vals_i = list(data_vals_i.values())[0]

                else:
                    # Otherwise assume that the dictionary contains x and y values; extract
                    # the y values
                    data_vals_i = data_vals_i["y"]

            data_vals_i = _generate_data_vals(data_vals=data_vals_i)

            # If not a list, then convert to a list
            if not isinstance(data_vals_i, list):

                data_vals_i = [data_vals_i]

            all_y_vals.extend(data_vals_i)

        all_y_vals = _flatten_list(all_y_vals)

        # Get the minimum and maximum values from the list
        expand_y = [min(all_y_vals), max(all_y_vals)]

    # Generate a function that will operate on single `x` values in the table body using both
    # the date and time format strings
    def fmt_nanoplot_fn(
        x: Any,
        plot_type: PlotType = plot_type,
        plot_height: str = plot_height,
        missing_vals: MissingVals = missing_vals,
        reference_line: Optional[Union[str, int, float]] = reference_line,
        reference_area: Optional[List[Any]] = reference_area,
        all_single_y_vals: Optional[List[Union[int, float]]] = all_single_y_vals,
        options_plots: Dict[str, Any] = options_plots,
    ) -> str:
        # If the `x` value is a Pandas 'NA', then return the same value
        # We have to pass in a dataframe to this function. Everything action that
        # requires a dataframe import should go through _tbl_data.
        if is_na(data_tbl, x):
            return x

        # Generate data vals from the input `x` value
        x = _generate_data_vals(data_vals=x)

        # TODO: where are tuples coming from? Need example / tests that induce tuples
        # If `x` is a tuple, then we have x and y values; otherwise, we only have y values
        if isinstance(x, tuple):

            y_vals = x[1]
            x_vals = x[0]

            # Ensure that both objects are lists
            if not isinstance(x_vals, list) or not isinstance(y_vals, list):
                raise ValueError("The 'x' and 'y' values must be lists.")

            # Ensure that the lists contain only numeric values (ints and floats)
            if not all(isinstance(val, (int, float)) for val in x_vals):
                raise ValueError("The 'x' values must be numeric.")

            # Ensure that the lengths of the x and y values are the same
            if len(x_vals) != len(y_vals):
                raise ValueError("The lengths of the 'x' and 'y' values must be the same.")

        else:
            y_vals = x
            x_vals = None

        nanoplot = _generate_nanoplot(
            y_vals=y_vals,
            y_ref_line=reference_line,
            y_ref_area=reference_area,
            x_vals=x_vals,
            expand_x=expand_x,
            expand_y=expand_y,
            missing_vals=missing_vals,
            all_single_y_vals=all_single_y_vals,
            plot_type=plot_type,
            svg_height=plot_height,
            **options_plots,
        )

        return nanoplot

    return fmt(self, fns=fmt_nanoplot_fn, columns=columns, rows=rows)


def _generate_data_vals(
    data_vals: Any, is_x_axis=False
) -> Union[List[float], Tuple[List[float], List[float]]]:
    """
    Generate a list of data values from the input data.

    Args:
        data_vals (Any): The input data values.

    Returns:
        List[Any]: A list of data values.
    """

    import re

    if isinstance(data_vals, list):

        # If the list contains string values, determine whether they are date values
        if all(isinstance(val, str) for val in data_vals):
            if not is_x_axis:
                raise ValueError("Only the x-axis of a nanoplot allows strings.")
            if re.search(r"\d{1,4}-\d{2}-\d{2}", data_vals[0]):
                data_vals = [_iso_to_date(val) for val in data_vals]

                # Transform the date values to numeric values
                data_vals = [val.toordinal() for val in data_vals]

        # If the cell value is a list of floats/ints, then return the same value

        # Check that the values within the list are numeric; missing values are allowed
        for val in data_vals:
            if val is not None and not isinstance(val, (int, float)):
                raise ValueError(f"The input data values must be numeric.\n\nValue received: {val}")

        return data_vals

    elif isinstance(data_vals, int) or isinstance(data_vals, float):
        return data_vals

    elif isinstance(data_vals, str):

        # If the cell value is a string, assume it is a value stream and convert to a list

        # Detect whether there are time values or numeric values in the string
        if re.search(r"\d{1,4}-\d{2}-\d{2}", data_vals) and is_x_axis:
            data_vals = _process_time_stream(data_vals)
        else:
            data_vals = _process_number_stream(data_vals)

    elif isinstance(data_vals, dict):

        # If the cell value is a dictionary, assume it contains data values
        # This is possibly for x and for y

        # Determine the number of keys in the dictionary
        num_keys = len(data_vals.keys())

        # If the dictionary contains only one key, then assume that the values are for y
        if num_keys == 1:

            data_vals = list(data_vals.values())[0]

            # The data values can be anything, so recursively call this function to process them
            data_vals = _generate_data_vals(data_vals=data_vals)

        if num_keys >= 2:

            # For two or more keys, we need to see if the 'x' and 'y' keys are present
            if "x" in data_vals and "y" in data_vals:

                x_vals: Any = data_vals["x"]
                y_vals: Any = data_vals["y"]

                # The data values can be anything, so recursively call this function to process them
                x_vals = _generate_data_vals(data_vals=x_vals, is_x_axis=True)
                y_vals = _generate_data_vals(data_vals=y_vals)

                # Ensure that the lengths of the x and y values are the same
                if len(x_vals) != len(y_vals):
                    raise ValueError("The lengths of the 'x' and 'y' values must be the same.")

                return x_vals, y_vals

            else:
                raise ValueError("The dictionary must contain 'x' and 'y' keys.")

    else:
        # Raise not implemented
        raise NotImplementedError("The input data values must be a string.")

    return data_vals


def _process_number_stream(data_vals: str) -> List[float]:
    """
    Process a string of numeric values and convert to a list of floats.

    Args:
        data_vals (str): The string of numeric values.

    Returns:
        List[float]: A list of numeric values.
    """

    import re

    number_stream = re.sub(r"[;,]", " ", data_vals)
    number_stream = re.sub(r"\\[|\\]", " ", number_stream)
    number_stream = re.sub(r"^\\s+|\\s+$", "", number_stream)
    number_stream = [val for val in number_stream.split()]
    number_stream = [re.sub(r"[\\(\\)a-dA-Df-zF-Z]", "", val) for val in number_stream]
    number_stream = [float(val) for val in number_stream]

    return number_stream


import re
from typing import List


def _process_time_stream(data_vals: str) -> List[float]:
    """
    Process a string of time values and convert to a list of floats.

    Args:
        data_vals (str): The string of time values.

    Returns:
        List[float]: A list of time values.
    """

    time_stream = re.split(r"\s*[;,]\s*", data_vals)
    time_stream = [val.replace("T", " ") for val in time_stream]
    time_stream_vals = [float(val) for val in time_stream]

    return time_stream_vals
