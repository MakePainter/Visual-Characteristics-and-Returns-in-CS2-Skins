"""Spectrum 2 CS2 skin market research pipeline.

Analyzes the complete 17-skin Spectrum 2 Factory New universe using
OpenSkin/Steam market history, U.S. Treasury 3-month rates, and image-derived
visual characteristics. Returns are gross of fees, bid-ask spread, slippage,
and taxes. Portfolio sorts are exploratory and are not trading recommendations.
"""

import colorsys
import math
import os
import time
from datetime import date, timedelta

import numpy as np
import pandas as pd
import requests
from colorthief_v3 import get_color, get_palette
from PIL import Image


API_BASE = 'https://api.openskin.dev/v1'
COLLECTION_NAME = 'Spectrum 2'
SKINS = [
    {'skin': 'Sawed-Off | Morris', 'rarity': 'Mil-Spec Grade'},
    {'skin': 'AUG | Triqua', 'rarity': 'Mil-Spec Grade'},
    {'skin': 'G3SG1 | Hunter', 'rarity': 'Mil-Spec Grade'},
    {'skin': 'Glock-18 | Off World', 'rarity': 'Mil-Spec Grade'},
    {'skin': 'MAC-10 | Oceanic', 'rarity': 'Mil-Spec Grade'},
    {'skin': 'Tec-9 | Cracked Opal', 'rarity': 'Mil-Spec Grade'},
    {'skin': 'SCAR-20 | Jungle Slipstream', 'rarity': 'Mil-Spec Grade'},
    {'skin': 'MP9 | Goo', 'rarity': 'Restricted'},
    {'skin': 'SG 553 | Phantom', 'rarity': 'Restricted'},
    {'skin': 'CZ75-Auto | Tacticat', 'rarity': 'Restricted'},
    {'skin': 'UMP-45 | Exposure', 'rarity': 'Restricted'},
    {'skin': 'XM1014 | Ziggy', 'rarity': 'Restricted'},
    {'skin': 'PP-Bizon | High Roller', 'rarity': 'Classified'},
    {'skin': 'M4A1-S | Leaded Glass', 'rarity': 'Classified'},
    {'skin': 'R8 Revolver | Llama Cannon', 'rarity': 'Classified'},
    {'skin': 'AK-47 | The Empress', 'rarity': 'Covert'},
    {'skin': 'P250 | See Ya Later', 'rarity': 'Covert'},
]
ANALYSIS_END_DATE = date(2026, 9, 28)
DAYS_OF_HISTORY = 1095
PALETTE_SIZE = 6
PORTFOLIO_FEATURES = ['Mean_Saturation', 'Mean_Brightness', 'Color_Diversity']
WINSOR_LOWER_QUANTILE = 0.01
WINSOR_UPPER_QUANTILE = 0.99
OUTPUT_DIR = 'spectrum2_output'
IMAGE_DIR = 'spectrum2_images'
SESSION = requests.Session()
SESSION.headers.update({'User-Agent': 'CS2-Spectrum2-Finance-Research/1.0'})

def market_name(skin_name):
    return f'{skin_name} (Factory New)'

def safe_float(value):
    if value is None:
        return None
    try:
        value = float(value)
        if math.isnan(value):
            return None
        return value
    except (TypeError, ValueError):
        return None

def request_json(method, url, **kwargs):
    """Make an HTTP request and return JSON, with useful errors."""
    try:
        response = SESSION.request(method, url, timeout=60, **kwargs)
    except requests.RequestException as exc:
        raise RuntimeError(f'Could not connect to OpenSkin:\n{exc}') from exc
    if not response.ok:
        try:
            detail = response.json()
        except ValueError:
            detail = response.text[:500]
        raise RuntimeError(f'OpenSkin returned HTTP {response.status_code}\nURL: {url}\nResponse: {detail}')
    try:
        return response.json()
    except ValueError as exc:
        raise RuntimeError(f'OpenSkin returned something that was not JSON.\nURL: {url}\nResponse: {response.text[:500]}') from exc

def hex_to_rgb(hex_color):
    """Convert '#RRGGBB' to (R, G, B)."""
    hex_color = str(hex_color).lstrip('#')
    if len(hex_color) != 6:
        raise ValueError(f'Unexpected hex color: {hex_color}')
    return (int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16))

def rgb_to_hsv(rgb):
    """Return HSV values on 0-1 scales."""
    r, g, b = [channel / 255.0 for channel in rgb]
    return colorsys.rgb_to_hsv(r, g, b)

def mean(values):
    values = [v for v in values if v is not None]
    if not values:
        return None
    return sum(values) / len(values)

def standard_deviation(values):
    values = [v for v in values if v is not None]
    if len(values) < 2:
        return None
    avg = sum(values) / len(values)
    variance = sum(((x - avg) ** 2 for x in values)) / (len(values) - 1)
    return math.sqrt(variance)

def get_current_market_data():
    items = [market_name(item['skin']) for item in SKINS]
    print(f'Requesting current prices for {len(items)} items...')
    data = request_json('POST', f'{API_BASE}/prices/batch', json={'items': items})
    return data

def extract_current_prices(current_data):
    """
    OpenSkin /v1/prices/batch returns:

        data -> item name -> item data

    The Steam data lives inside:

        item_data["prices"]["steam"]
    """
    rows = []
    data = current_data.get('data', {})
    if not isinstance(data, dict):
        data = {}
    result_list = current_data.get('results', [])
    results_by_item = {}
    if isinstance(result_list, list):
        for result in result_list:
            if isinstance(result, dict):
                item_name = result.get('item')
                if item_name:
                    results_by_item[item_name] = result
    for metadata in SKINS:
        item_name = market_name(metadata['skin'])
        item_data = data.get(item_name)
        if not isinstance(item_data, dict):
            item_data = results_by_item.get(item_name, {})
        prices = item_data.get('prices', {})
        if not isinstance(prices, dict):
            prices = {}
        steam = prices.get('steam', {})
        if not isinstance(steam, dict):
            steam = {}
        if not steam:
            direct_steam = item_data.get('steam', {})
            if isinstance(direct_steam, dict):
                steam = direct_steam
        rows.append(
            {
                'Market_Name': item_name,
                'Current_Steam_Ask': safe_float(steam.get('ask')),
                'Current_Steam_Bid': safe_float(steam.get('bid')),
                'Current_Steam_Median': safe_float(steam.get('median')),
                'Steam_Buy_Order_Count': safe_float(steam.get('buy_order_count')),
                'Steam_Sell_Order_Count': safe_float(steam.get('sell_order_count')),
                'Icon_URL': item_data.get('icon_url'),
                'Updated_At': item_data.get('updated_at'),
            }
        )
    return pd.DataFrame(rows)

def download_image(image_url, output_path):
    if not image_url:
        return False
    try:
        response = SESSION.get(image_url, timeout=60)
    except requests.RequestException as exc:
        print(f'    Image download failed: {exc}')
        return False
    if not response.ok:
        print(f'    Image download failed: HTTP {response.status_code}')
        return False
    try:
        with open(output_path, 'wb') as file:
            file.write(response.content)
        with Image.open(output_path) as image:
            image.verify()
        return True
    except Exception as exc:
        print(f'    Image verification failed: {exc}')
        return False

def analyze_image(image_path):
    """Extract image characteristics from visible weapon pixels only.

    Steam icon PNGs use transparency around the weapon. Fully transparent
    pixels are excluded so the canvas does not dilute color statistics or
    influence the Color Thief palette. All visible weapon pixels are retained.
    """
    with Image.open(image_path) as original:
        image = original.convert('RGBA')
        image.thumbnail((500, 500))
        rgba_pixels = list(image.get_flattened_data())
        width, height = image.size

    visible_mask = [pixel[3] > 0 for pixel in rgba_pixels]
    pixels = [pixel[:3] for pixel in rgba_pixels if pixel[3] > 0]
    if not pixels:
        raise ValueError('Image contains no visible pixels.')

    red = [pixel[0] for pixel in pixels]
    green = [pixel[1] for pixel in pixels]
    blue = [pixel[2] for pixel in pixels]
    mean_r = mean(red)
    mean_g = mean(green)
    mean_b = mean(blue)
    std_r = standard_deviation(red)
    std_g = standard_deviation(green)
    std_b = standard_deviation(blue)

    hsv_values = [rgb_to_hsv(pixel) for pixel in pixels]
    hue = [value[0] for value in hsv_values]
    saturation = [value[1] for value in hsv_values]
    brightness = [value[2] for value in hsv_values]
    hue_angles = [2 * math.pi * h for h in hue]
    hue_sin = mean([math.sin(angle) for angle in hue_angles])
    hue_cos = mean([math.cos(angle) for angle in hue_angles])
    if hue_sin is not None and hue_cos is not None:
        mean_hue = math.atan2(hue_sin, hue_cos) / (2 * math.pi) % 1
    else:
        mean_hue = None

    mean_saturation = mean(saturation)
    mean_brightness = mean(brightness)
    std_saturation = standard_deviation(saturation)
    std_brightness = standard_deviation(brightness)

    luminance = [
        0.2126 * pixel[0] + 0.7152 * pixel[1] + 0.0722 * pixel[2]
        for pixel in pixels
    ]
    pixel_contrast = standard_deviation(luminance)

    # Color Thief works from an image file. Build a temporary RGB image that
    # contains only visible weapon pixels, tightly cropped to the weapon bounds.
    alpha = image.getchannel('A')
    bbox = alpha.getbbox()
    if bbox is None:
        raise ValueError('Image contains no visible pixels.')
    cropped = image.crop(bbox)
    cropped_pixels = list(cropped.get_flattened_data())
    visible_cropped = [p[:3] for p in cropped_pixels if p[3] > 0]
    palette_source = Image.new('RGB', (len(visible_cropped), 1))
    palette_source.putdata(visible_cropped)
    palette_path = image_path + '.visible_palette.png'
    palette_source.save(palette_path)
    try:
        dominant_color = get_color(palette_path)
        palette = get_palette(palette_path, color_count=PALETTE_SIZE)
    finally:
        if os.path.exists(palette_path):
            os.remove(palette_path)

    dominant_rgb = hex_to_rgb(dominant_color.hex())
    palette_rgb = [hex_to_rgb(color.hex()) for color in palette]

    pairwise_distances = []
    for i in range(len(palette_rgb)):
        for j in range(i + 1, len(palette_rgb)):
            r1, g1, b1 = palette_rgb[i]
            r2, g2, b2 = palette_rgb[j]
            distance = math.sqrt(
                (r1 - r2) ** 2 + (g1 - g2) ** 2 + (b1 - b2) ** 2
            )
            pairwise_distances.append(distance)
    color_diversity = mean(pairwise_distances)
    dominant_hue, dominant_saturation, dominant_brightness = rgb_to_hsv(dominant_rgb)

    # Count an edge only when both neighboring pixels are visible. This avoids
    # treating the weapon/transparency boundary as artwork texture.
    gray_values = [
        0.2126 * p[0] + 0.7152 * p[1] + 0.0722 * p[2]
        for p in rgba_pixels
    ]
    if width > 1 and height > 1:
        edge_count = 0
        edge_total = 0
        threshold = 25
        for y in range(height):
            for x in range(width):
                index = y * width + x
                if not visible_mask[index]:
                    continue
                current = gray_values[index]
                if x + 1 < width:
                    right_index = index + 1
                    if visible_mask[right_index]:
                        if abs(current - gray_values[right_index]) >= threshold:
                            edge_count += 1
                        edge_total += 1
                if y + 1 < height:
                    below_index = index + width
                    if visible_mask[below_index]:
                        if abs(current - gray_values[below_index]) >= threshold:
                            edge_count += 1
                        edge_total += 1
        edge_density = edge_count / edge_total if edge_total else None
    else:
        edge_density = None

    row = {
        'Mean_Red': mean_r,
        'Mean_Green': mean_g,
        'Mean_Blue': mean_b,
        'Std_Red': std_r,
        'Std_Green': std_g,
        'Std_Blue': std_b,
        'Mean_Hue': mean_hue,
        'Mean_Saturation': mean_saturation,
        'Mean_Brightness': mean_brightness,
        'Std_Saturation': std_saturation,
        'Std_Brightness': std_brightness,
        'Pixel_Contrast': pixel_contrast,
        'Dominant_Red': dominant_rgb[0],
        'Dominant_Green': dominant_rgb[1],
        'Dominant_Blue': dominant_rgb[2],
        'Dominant_Hue': dominant_hue,
        'Dominant_Saturation': dominant_saturation,
        'Dominant_Brightness': dominant_brightness,
        'Dominant_Hex': dominant_color.hex(),
        'Color_Diversity': color_diversity,
        'Edge_Density': edge_density,
    }
    for index in range(PALETTE_SIZE):
        if index < len(palette_rgb):
            rgb = palette_rgb[index]
            row[f'Palette_{index + 1}_R'] = rgb[0]
            row[f'Palette_{index + 1}_G'] = rgb[1]
            row[f'Palette_{index + 1}_B'] = rgb[2]
            row[f'Palette_{index + 1}_Hex'] = palette[index].hex()
        else:
            row[f'Palette_{index + 1}_R'] = None
            row[f'Palette_{index + 1}_G'] = None
            row[f'Palette_{index + 1}_B'] = None
            row[f'Palette_{index + 1}_Hex'] = None
    return row

def get_visual_data(current_prices):
    rows = []
    for _, price_row in current_prices.iterrows():
        item_name = price_row['Market_Name']
        icon_url = price_row['Icon_URL']
        safe_filename = item_name.replace('|', '_').replace(':', '_').replace('/', '_').replace('\\', '_').replace('*', '_').replace('?', '_').replace('"', '_').replace('<', '_').replace('>', '_')
        image_path = os.path.join(IMAGE_DIR, safe_filename + '.png')
        print(f'  {item_name}')
        if not icon_url:
            print('    No icon URL.')
            continue
        if not os.path.exists(image_path):
            print('    Downloading image...')
            success = download_image(icon_url, image_path)
            if not success:
                continue
        else:
            print('    Image already exists.')
        try:
            features = analyze_image(image_path)
        except Exception as exc:
            print(f'    ERROR analyzing image: {exc}')
            continue
        features['Market_Name'] = item_name
        features['Icon_URL'] = icon_url
        features['Image_Path'] = image_path
        rows.append(features)
    columns = ['Market_Name', 'Icon_URL', 'Image_Path', 'Mean_Red', 'Mean_Green', 'Mean_Blue', 'Std_Red', 'Std_Green', 'Std_Blue', 'Mean_Hue', 'Mean_Saturation', 'Mean_Brightness', 'Std_Saturation', 'Std_Brightness', 'Pixel_Contrast', 'Dominant_Red', 'Dominant_Green', 'Dominant_Blue', 'Dominant_Hue', 'Dominant_Saturation', 'Dominant_Brightness', 'Dominant_Hex', 'Color_Diversity', 'Edge_Density']
    for index in range(PALETTE_SIZE):
        columns.extend([f'Palette_{index + 1}_R', f'Palette_{index + 1}_G', f'Palette_{index + 1}_B', f'Palette_{index + 1}_Hex'])
    return pd.DataFrame(rows, columns=columns)

def get_history():
    items = [market_name(item['skin']) for item in SKINS]
    end_date = ANALYSIS_END_DATE
    start_date = end_date - timedelta(days=DAYS_OF_HISTORY)
    print(f'Requesting Steam daily history from {start_date} to {end_date}...')
    response = request_json('POST', f'{API_BASE}/history/batch', json={'items': items, 'marketplace': 'steam', 'from': start_date.isoformat(), 'to': end_date.isoformat(), 'interval': 'daily'})
    return response

def history_to_dataframe(history_data):
    data = history_data.get('data', {})
    rows = []
    if not isinstance(data, dict):
        return pd.DataFrame(columns=['Market_Name', 'Date', 'Price', 'Volume'])
    for item_name, points in data.items():
        if not isinstance(points, list):
            continue
        for point in points:
            if not isinstance(point, dict):
                continue
            timestamp = point.get('timestamp')
            price = safe_float(point.get('price'))
            volume = safe_float(point.get('volume'))
            if timestamp is None or price is None or price <= 0:
                continue
            rows.append({'Market_Name': item_name, 'Date': pd.to_datetime(timestamp, utc=True).tz_convert(None).normalize(), 'Price': price, 'Volume': volume})
    if not rows:
        return pd.DataFrame(columns=['Market_Name', 'Date', 'Price', 'Volume'])
    df = pd.DataFrame(rows)
    df['Date'] = normalize_datetime_series(df['Date'])
    df = df.sort_values(['Market_Name', 'Date']).drop_duplicates(['Market_Name', 'Date'], keep='last').reset_index(drop=True)
    return df
TREASURY_XML_URL = 'https://home.treasury.gov/resource-center/data-chart-center/interest-rates/pages/xml'

def get_risk_free_rates(start_date, end_date):
    """
    Download historical daily 3-month U.S. Treasury
    constant-maturity rates directly from the U.S. Treasury.

    Source:
        U.S. Department of the Treasury
        Daily Treasury Par Yield Curve Rates

    Treasury field:
        BC_3MONTH

    BC_3MONTH is the 3-month constant-maturity Treasury
    par yield, expressed as an annual percentage rate.

    We convert:
        4.25% -> 0.0425 annual decimal rate

    and then:
        0.0425 / 365
        -> daily decimal risk-free rate

    The Treasury XML feed is used instead of FRED so the
    project does not depend on the FRED server.
    """
    start_date = pd.to_datetime(start_date).date()
    end_date = pd.to_datetime(end_date).date()
    print(f'Requesting daily 3-month Treasury rates from the U.S. Treasury for {start_date} to {end_date}...')
    years = range(start_date.year, end_date.year + 1)
    all_rows = []
    for year in years:
        print(f'  Requesting Treasury yield data for {year}...')
        params = {'data': 'daily_treasury_yield_curve', 'field_tdr_date_value': str(year)}
        max_attempts = 3
        response = None
        last_error = None
        for attempt in range(1, max_attempts + 1):
            try:
                print(f'    Treasury request {attempt}/{max_attempts}...')
                response = SESSION.get(TREASURY_XML_URL, params=params, timeout=(15, 45))
                response.raise_for_status()
                if not response.content:
                    raise RuntimeError('Treasury returned an empty response.')
                break
            except (requests.RequestException, RuntimeError) as exc:
                last_error = exc
                if attempt < max_attempts:
                    wait_seconds = 3 * attempt
                    print(f'    Request failed: {exc}')
                    print(f'    Retrying in {wait_seconds} seconds...')
                    time.sleep(wait_seconds)
                else:
                    raise RuntimeError(f'Could not retrieve U.S. Treasury yield data for {year}.\nLast error: {exc}') from exc
        try:
            import xml.etree.ElementTree as ET
            root = ET.fromstring(response.content)
        except Exception as exc:
            raise RuntimeError(f'Treasury returned data for {year}, but the XML could not be parsed: {exc}') from exc
        entries = []
        for element in root.iter():
            if element.tag.endswith('entry'):
                entries.append(element)
        if not entries:
            raise RuntimeError(f'Treasury returned no XML entries for {year}.')
        year_rows = []
        for entry in entries:
            date_value = None
            three_month_value = None
            for element in entry.iter():
                tag = element.tag
                if '}' in tag:
                    local_name = tag.split('}', 1)[1]
                else:
                    local_name = tag
                text_value = element.text.strip() if element.text else None
                if local_name == 'NEW_DATE':
                    date_value = text_value
                elif local_name == 'BC_3MONTH':
                    three_month_value = text_value
            if date_value is None:
                continue
            if three_month_value is None:
                continue
            if str(three_month_value).strip().upper() == 'N/A':
                continue
            try:
                three_month_value = float(three_month_value)
            except (TypeError, ValueError):
                continue
            parsed_date = pd.to_datetime(date_value, errors='coerce')
            if pd.isna(parsed_date):
                continue
            year_rows.append({'Date': parsed_date.normalize(), 'DGS3MO': three_month_value})
        if not year_rows:
            raise RuntimeError(f'Treasury returned XML for {year}, but no usable BC_3MONTH observations were found.')
        print(f'    Treasury 3-month observations: {len(year_rows)}')
        all_rows.extend(year_rows)
    df = pd.DataFrame(all_rows)
    if df.empty:
        raise RuntimeError('Treasury returned no usable 3-month Treasury observations.')
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce').dt.normalize()
    df['DGS3MO'] = pd.to_numeric(df['DGS3MO'], errors='coerce')
    df = df.dropna(subset=['Date', 'DGS3MO'])
    df = df[(df['Date'] >= pd.Timestamp(start_date)) & (df['Date'] <= pd.Timestamp(end_date))].copy()
    df = df.sort_values('Date')
    df = df.drop_duplicates(subset=['Date'], keep='last')
    if df.empty:
        raise RuntimeError(f'Treasury returned data, but none of the observations fall inside the requested period {start_date} to {end_date}.')
    df['Risk_Free_Annual'] = df['DGS3MO'] / 100.0
    df['Risk_Free_Daily'] = df['Risk_Free_Annual'] / 365.0
    treasury_output = os.path.join(OUTPUT_DIR, 'treasury_3month_risk_free.csv')
    df.to_csv(treasury_output, index=False)
    print(f'Treasury risk-free observations collected: {len(df)}')
    print(f'Treasury data saved to: {treasury_output}')
    print(f"Treasury date range: {df['Date'].min().date()} to {df['Date'].max().date()}")
    print(f"Latest 3-month Treasury rate: {df.iloc[-1]['DGS3MO']:.2f}%")
    return df[['Date', 'DGS3MO', 'Risk_Free_Annual', 'Risk_Free_Daily']].copy()

def normalize_datetime_series(values):
    """Return a consistently typed datetime Series for pandas merges."""
    result = pd.to_datetime(values, errors='coerce')
    if isinstance(result, pd.DatetimeIndex):
        result = pd.Series(result)
    return result.astype('datetime64[ns]')

def align_rf_to_dates(dates, rf_data):
    """
    Match each requested date to the most recent available
    Treasury observation. This carries the latest business-day
    Treasury rate across weekends and other non-publication days.
    """
    base = pd.DataFrame({'Date': normalize_datetime_series(dates)}).dropna()
    rf = rf_data[['Date', 'Risk_Free_Annual', 'Risk_Free_Daily']].copy()
    rf['Date'] = normalize_datetime_series(rf['Date'])
    rf['Risk_Free_Annual'] = pd.to_numeric(rf['Risk_Free_Annual'], errors='coerce')
    rf['Risk_Free_Daily'] = pd.to_numeric(rf['Risk_Free_Daily'], errors='coerce')
    base = base.sort_values('Date')
    rf = rf.dropna(subset=['Date', 'Risk_Free_Annual']).sort_values('Date').drop_duplicates('Date', keep='last')
    aligned = pd.merge_asof(base, rf, on='Date', direction='backward')
    if aligned['Risk_Free_Annual'].isna().any():
        first_missing = aligned.loc[aligned['Risk_Free_Annual'].isna(), 'Date'].iloc[0]
        raise RuntimeError(f'No Treasury risk-free observation exists on or before {first_missing.date()}.')
    return aligned['Risk_Free_Daily'].reset_index(drop=True)

def calculate_max_drawdown(returns):
    if returns.empty:
        return None
    growth = (1.0 + returns).cumprod()
    running_max = growth.cummax()
    drawdown = growth / running_max - 1.0
    return float(drawdown.min())

def calculate_metrics(history_df, rf_data):
    rows = []
    for item_name, group in history_df.groupby('Market_Name'):
        group = group.copy()
        group['Date'] = normalize_datetime_series(group['Date'])
        group['Price'] = pd.to_numeric(group['Price'], errors='coerce')
        group = group.dropna(subset=['Date', 'Price']).sort_values('Date').drop_duplicates('Date', keep='last').reset_index(drop=True)
        if len(group) < 2:
            continue
        group['Previous_Date'] = group['Date'].shift(1)
        group['Days_Since_Last_Observation'] = (group['Date'] - group['Previous_Date']).dt.days
        group['Daily_Return'] = group['Price'].pct_change(fill_method=None)
        valid_daily = group['Days_Since_Last_Observation'] == 1
        daily_returns = group.loc[valid_daily, 'Daily_Return'].dropna().reset_index(drop=True)
        if daily_returns.empty:
            continue
        return_dates = group.loc[valid_daily, 'Date'].reset_index(drop=True)
        daily_rf = align_rf_to_dates(return_dates, rf_data)
        excess_daily_returns = daily_returns - daily_rf
        first_price = float(group['Price'].iloc[0])
        last_price = float(group['Price'].iloc[-1])
        total_return = last_price / first_price - 1.0
        day_count = (group['Date'].iloc[-1] - group['Date'].iloc[0]).days
        if day_count > 0 and first_price > 0:
            annualized_return = (last_price / first_price) ** (365.0 / day_count) - 1.0
        else:
            annualized_return = None
        annualized_volatility = float(daily_returns.std(ddof=1)) * math.sqrt(365.0) if len(daily_returns) >= 2 else None
        daily_std = excess_daily_returns.std(ddof=1)
        if pd.notna(daily_std) and daily_std > 0:
            sharpe_ratio = excess_daily_returns.mean() / daily_std * math.sqrt(365.0)
        else:
            sharpe_ratio = None
        max_drawdown = calculate_max_drawdown(daily_returns)
        volume = pd.to_numeric(group['Volume'], errors='coerce')
        observed_days = len(group)
        expected_days = day_count + 1 if day_count >= 0 else None
        missing_days = expected_days - observed_days if expected_days is not None else None
        coverage_percent = observed_days / expected_days if expected_days and expected_days > 0 else None
        rows.append({'Market_Name': item_name, 'Start_Date': group['Date'].iloc[0], 'End_Date': group['Date'].iloc[-1], 'Start_Price': first_price, 'End_Price': last_price, 'Total_Return': total_return, 'Annualized_Return': annualized_return, 'Annualized_Volatility': annualized_volatility, 'Sharpe_Ratio': sharpe_ratio, 'Max_Drawdown': max_drawdown, 'Average_Daily_Return': float(daily_returns.mean()), 'Positive_Day_Percentage': float((daily_returns > 0).mean()), 'Average_Daily_Volume': float(volume.mean()) if volume.notna().any() else None, 'Total_Volume': float(volume.sum()) if volume.notna().any() else None, 'Observed_Days': observed_days, 'Expected_Days': expected_days, 'Missing_Days': missing_days, 'Coverage_Percent': coverage_percent, 'Observations': len(daily_returns), 'Gross_Return_Note': 'Price return before Steam fees, bid-ask spread, slippage, and taxes.'})
    return pd.DataFrame(rows)

def make_daily_return_data(history_df, rf_data):
    if history_df.empty:
        return pd.DataFrame()
    df = history_df.copy()
    df['Date'] = normalize_datetime_series(df['Date'])
    df['Price'] = pd.to_numeric(df['Price'], errors='coerce')
    df = df.dropna(subset=['Market_Name', 'Date', 'Price']).sort_values(['Market_Name', 'Date']).drop_duplicates(['Market_Name', 'Date'], keep='last').reset_index(drop=True)
    df['Previous_Date'] = df.groupby('Market_Name')['Date'].shift(1)
    df['Days_Since_Last_Observation'] = (df['Date'] - df['Previous_Date']).dt.days
    df['Daily_Return'] = df.groupby('Market_Name')['Price'].pct_change(fill_method=None)
    df.loc[df['Days_Since_Last_Observation'] != 1, 'Daily_Return'] = np.nan
    df['Log_Return'] = np.where(df['Daily_Return'].notna() & (df['Daily_Return'] > -1), np.log1p(df['Daily_Return']), np.nan)
    df['Daily_Risk_Free'] = np.nan
    valid_dates = df['Daily_Return'].notna()
    if valid_dates.any():
        df.loc[valid_dates, 'Daily_Risk_Free'] = align_rf_to_dates(df.loc[valid_dates, 'Date'].reset_index(drop=True), rf_data).to_numpy()
    df['Excess_Daily_Return'] = df['Daily_Return'] - df['Daily_Risk_Free']
    return df.sort_values(['Market_Name', 'Date']).reset_index(drop=True)

def winsorize_daily_returns(daily_returns, lower_quantile=0.01, upper_quantile=0.99):
    """Create a robustness copy using pooled cross-asset daily-return quantiles.

    The thresholds are estimated once from all valid skin-day returns and then
    applied uniformly to every skin. Raw returns are retained for auditability.
    """
    if daily_returns.empty:
        return daily_returns.copy(), None, None
    if not 0 <= lower_quantile < upper_quantile <= 1:
        raise ValueError('Winsorization quantiles must satisfy 0 <= lower < upper <= 1.')

    result = daily_returns.copy()
    raw = pd.to_numeric(result['Daily_Return'], errors='coerce')
    valid = raw.dropna()
    if valid.empty:
        return result, None, None

    lower = float(valid.quantile(lower_quantile))
    upper = float(valid.quantile(upper_quantile))
    result['Daily_Return_Raw'] = raw
    result['Daily_Return_Winsorized'] = raw.clip(lower=lower, upper=upper)
    result['Was_Winsorized'] = raw.notna() & ((raw < lower) | (raw > upper))
    result['Winsorization_Direction'] = np.select(
        [raw < lower, raw > upper],
        ['Lower', 'Upper'],
        default='None',
    )
    result.loc[raw.isna(), 'Winsorization_Direction'] = np.nan
    result['Winsor_Lower_Bound'] = lower
    result['Winsor_Upper_Bound'] = upper
    result['Excess_Daily_Return_Winsorized'] = (
        result['Daily_Return_Winsorized'] - result['Daily_Risk_Free']
    )
    return result, lower, upper


def calculate_winsorized_metrics(winsorized_returns):
    """Calculate return-based robustness metrics from winsorized daily returns."""
    rows = []
    if winsorized_returns.empty:
        return pd.DataFrame(rows)

    for item_name, group in winsorized_returns.groupby('Market_Name'):
        group = group.copy()
        group['Date'] = normalize_datetime_series(group['Date'])
        returns = pd.to_numeric(group['Daily_Return_Winsorized'], errors='coerce')
        risk_free = pd.to_numeric(group['Daily_Risk_Free'], errors='coerce')
        valid = group.loc[returns.notna()].copy()
        if valid.empty:
            continue

        returns = pd.to_numeric(valid['Daily_Return_Winsorized'], errors='coerce')
        risk_free = pd.to_numeric(valid['Daily_Risk_Free'], errors='coerce')
        excess = returns - risk_free
        wealth = (1.0 + returns).cumprod()
        compounded_return = float(wealth.iloc[-1] - 1.0)
        start_date = valid['Date'].iloc[0]
        end_date = valid['Date'].iloc[-1]
        calendar_days = (end_date - start_date).days
        if calendar_days > 0 and wealth.iloc[-1] > 0:
            annualized_return = float(wealth.iloc[-1] ** (365.0 / calendar_days) - 1.0)
        else:
            annualized_return = None
        volatility = float(returns.std(ddof=1) * math.sqrt(365.0)) if len(returns) >= 2 else None
        excess_std = excess.std(ddof=1)
        sharpe = (
            float(excess.mean() / excess_std * math.sqrt(365.0))
            if pd.notna(excess_std) and excess_std > 0
            else None
        )
        max_drawdown = calculate_max_drawdown(returns)
        rows.append({
            'Market_Name': item_name,
            'Start_Date': start_date,
            'End_Date': end_date,
            'Total_Return': compounded_return,
            'Annualized_Return': annualized_return,
            'Annualized_Volatility': volatility,
            'Sharpe_Ratio': sharpe,
            'Max_Drawdown': max_drawdown,
            'Average_Daily_Return': float(returns.mean()),
            'Positive_Day_Percentage': float((returns > 0).mean()),
            'Observations': len(returns),
            'Winsorized_Observations': int(valid['Was_Winsorized'].sum()),
            'Robustness_Note': (
                'Daily returns are pooled 1st/99th percentile winsorized. '
                'Total and annualized returns are synthetic compounded-return robustness measures.'
            ),
        })
    return pd.DataFrame(rows)


def make_winsorized_price_index(winsorized_returns):
    """Build synthetic price indices so portfolio logic can be rerun on capped returns."""
    rows = []
    if winsorized_returns.empty:
        return pd.DataFrame(columns=['Market_Name', 'Date', 'Price', 'Volume'])

    for item_name, group in winsorized_returns.groupby('Market_Name'):
        group = group.copy()
        group['Date'] = normalize_datetime_series(group['Date'])
        group['Previous_Date'] = normalize_datetime_series(group['Previous_Date'])
        group['Daily_Return_Winsorized'] = pd.to_numeric(
            group['Daily_Return_Winsorized'], errors='coerce'
        )
        valid = group.dropna(subset=['Date', 'Previous_Date', 'Daily_Return_Winsorized']).sort_values('Date')
        if valid.empty:
            continue

        index_value = 1.0
        first_previous_date = valid.iloc[0]['Previous_Date']
        rows.append({'Market_Name': item_name, 'Date': first_previous_date, 'Price': index_value, 'Volume': np.nan})
        last_date = first_previous_date
        for _, row in valid.iterrows():
            if row['Previous_Date'] != last_date:
                last_date = row['Previous_Date']
                rows.append({'Market_Name': item_name, 'Date': last_date, 'Price': index_value, 'Volume': np.nan})
            index_value *= 1.0 + row['Daily_Return_Winsorized']
            last_date = row['Date']
            rows.append({'Market_Name': item_name, 'Date': last_date, 'Price': index_value, 'Volume': np.nan})

    result = pd.DataFrame(rows)
    if result.empty:
        return result
    return result.sort_values(['Market_Name', 'Date']).drop_duplicates(
        ['Market_Name', 'Date'], keep='last'
    ).reset_index(drop=True)


def make_robustness_summary(raw_metrics, winsorized_metrics, lower, upper, winsorized_returns):
    """Create a compact audit table describing the robustness specification."""
    valid = winsorized_returns['Daily_Return_Raw'].notna()
    flagged = winsorized_returns.loc[valid, 'Was_Winsorized'].fillna(False)
    summary = pd.DataFrame([
        {'Statistic': 'Lower winsorization quantile', 'Value': WINSOR_LOWER_QUANTILE},
        {'Statistic': 'Upper winsorization quantile', 'Value': WINSOR_UPPER_QUANTILE},
        {'Statistic': 'Lower daily-return bound', 'Value': lower},
        {'Statistic': 'Upper daily-return bound', 'Value': upper},
        {'Statistic': 'Valid daily returns', 'Value': int(valid.sum())},
        {'Statistic': 'Winsorized observations', 'Value': int(flagged.sum())},
        {'Statistic': 'Percent winsorized', 'Value': float(flagged.mean()) if len(flagged) else np.nan},
    ])
    comparison = raw_metrics[['Market_Name', 'Annualized_Volatility', 'Sharpe_Ratio', 'Max_Drawdown']].merge(
        winsorized_metrics[['Market_Name', 'Annualized_Volatility', 'Sharpe_Ratio', 'Max_Drawdown']],
        on='Market_Name',
        how='inner',
        suffixes=('_Raw', '_Winsorized'),
    )
    return summary, comparison


def add_skin_metadata(master):
    metadata_df = pd.DataFrame(SKINS)
    metadata_df['Market_Name'] = metadata_df['skin'].apply(market_name)
    metadata_df = metadata_df.rename(columns={'skin': 'Skin', 'rarity': 'Rarity'})
    return metadata_df.merge(master, on='Market_Name', how='right')

def make_correlation_table(master):
    visual_columns = ['Mean_Red', 'Mean_Green', 'Mean_Blue', 'Mean_Hue', 'Mean_Saturation', 'Mean_Brightness', 'Std_Saturation', 'Std_Brightness', 'Pixel_Contrast', 'Color_Diversity', 'Edge_Density', 'Dominant_Saturation', 'Dominant_Brightness']
    financial_columns = ['Total_Return', 'Annualized_Return', 'Annualized_Volatility', 'Sharpe_Ratio', 'Max_Drawdown']
    rows = []
    for visual in visual_columns:
        for financial in financial_columns:
            if visual not in master.columns:
                continue
            if financial not in master.columns:
                continue
            pair = master[[visual, financial]].dropna()
            n = len(pair)
            if n < 3:
                pearson = None
                spearman = None
            else:
                pearson = pair[visual].corr(pair[financial], method='pearson')
                ranked_pair = pair.rank(method='average')
                spearman = ranked_pair[visual].corr(ranked_pair[financial], method='pearson')
            rows.append({'Visual_Feature': visual, 'Financial_Metric': financial, 'N': n, 'Pearson_Correlation': pearson, 'Spearman_Correlation': spearman})
    return pd.DataFrame(rows)

def get_common_portfolio_period(price_data, members):
    """Return the first and last dates observed for every member of the universe.

    The common endpoints make cumulative High/Low portfolio returns directly
    comparable without forward-filling missing prices. Intermediate observations
    remain portfolio-specific so valid market data are not discarded unnecessarily.
    """
    if price_data.empty or not members:
        return None, None

    data = price_data.copy()
    data['Date'] = normalize_datetime_series(data['Date'])
    data['Price'] = pd.to_numeric(data['Price'], errors='coerce')
    data = data[data['Market_Name'].isin(members)].dropna(
        subset=['Market_Name', 'Date', 'Price']
    )

    matrix = data.pivot_table(
        index='Date', columns='Market_Name', values='Price', aggfunc='last'
    ).sort_index()
    if not all(member in matrix.columns for member in members):
        return None, None

    common_prices = matrix[members].dropna(how='any')
    if len(common_prices) < 2:
        return None, None

    return common_prices.index[0], common_prices.index[-1]


def get_portfolio_return_series(price_data, members, start_date=None, end_date=None):
    """Build one-day buy-and-hold portfolio returns inside fixed endpoints."""
    data = price_data.copy()
    if data.empty or not members:
        return pd.Series(dtype=float, name='Portfolio_Return')

    data['Date'] = normalize_datetime_series(data['Date'])
    data['Price'] = pd.to_numeric(data['Price'], errors='coerce')
    data = data[data['Market_Name'].isin(members)].dropna(subset=['Date', 'Price'])
    matrix = data.pivot_table(
        index='Date', columns='Market_Name', values='Price', aggfunc='last'
    ).sort_index()
    if not all(member in matrix.columns for member in members):
        return pd.Series(dtype=float, name='Portfolio_Return')

    matrix = matrix[members]
    if start_date is not None:
        matrix = matrix.loc[matrix.index >= pd.Timestamp(start_date)]
    if end_date is not None:
        matrix = matrix.loc[matrix.index <= pd.Timestamp(end_date)]
    matrix = matrix.dropna(how='any')
    if len(matrix) < 2:
        return pd.Series(dtype=float, name='Portfolio_Return')

    # Fixed endpoints must themselves be observed for every portfolio member.
    if start_date is not None and matrix.index[0] != pd.Timestamp(start_date):
        return pd.Series(dtype=float, name='Portfolio_Return')
    if end_date is not None and matrix.index[-1] != pd.Timestamp(end_date):
        return pd.Series(dtype=float, name='Portfolio_Return')

    shares = 1.0 / len(members) / matrix.iloc[0]
    value = (matrix * shares).sum(axis=1)
    portfolio_returns = value.pct_change(fill_method=None)
    gaps = value.index.to_series().diff().dt.days
    portfolio_returns[gaps != 1] = np.nan
    return portfolio_returns.dropna().rename('Portfolio_Return')


def portfolio_metrics(price_data, members, rf_data, portfolio_name='', start_date=None, end_date=None):
    """Calculate equal-weight buy-and-hold metrics over fixed common endpoints."""
    if not members or price_data.empty:
        return None

    data = price_data.copy()
    data['Date'] = normalize_datetime_series(data['Date'])
    data['Price'] = pd.to_numeric(data['Price'], errors='coerce')
    data = data[data['Market_Name'].isin(members)].dropna(
        subset=['Market_Name', 'Date', 'Price']
    )
    if data.empty:
        return None

    price_matrix = data.pivot_table(
        index='Date', columns='Market_Name', values='Price', aggfunc='last'
    ).sort_index()
    if not all(member in price_matrix.columns for member in members):
        return None

    price_matrix = price_matrix[members]
    if start_date is not None:
        price_matrix = price_matrix.loc[price_matrix.index >= pd.Timestamp(start_date)]
    if end_date is not None:
        price_matrix = price_matrix.loc[price_matrix.index <= pd.Timestamp(end_date)]

    # Use only dates with observed prices for every member of this portfolio.
    # No prices are forward-filled. Intermediate observation counts may therefore
    # differ across portfolios even though all cumulative returns share endpoints.
    price_matrix = price_matrix.dropna(how='any')
    if len(price_matrix) < 2:
        return None

    if start_date is not None and price_matrix.index[0] != pd.Timestamp(start_date):
        return None
    if end_date is not None and price_matrix.index[-1] != pd.Timestamp(end_date):
        return None

    number_of_skins = len(members)
    initial_weight = 1.0 / number_of_skins
    starting_prices = price_matrix.iloc[0]
    shares = initial_weight / starting_prices
    portfolio_value = (price_matrix * shares).sum(axis=1)

    portfolio_returns = portfolio_value.pct_change(fill_method=None)
    portfolio_gaps = portfolio_value.index.to_series().diff().dt.days
    portfolio_returns[portfolio_gaps != 1] = np.nan
    portfolio_returns = portfolio_returns.dropna()
    if portfolio_returns.empty:
        return None

    actual_start_date = portfolio_value.index[0]
    actual_end_date = portfolio_value.index[-1]
    days = (actual_end_date - actual_start_date).days
    if days <= 0:
        return None

    total_return = portfolio_value.iloc[-1] / portfolio_value.iloc[0] - 1.0
    annualized_return = (portfolio_value.iloc[-1] / portfolio_value.iloc[0]) ** (365.0 / days) - 1.0
    daily_std = portfolio_returns.std(ddof=1)
    annualized_volatility = daily_std * np.sqrt(365.0)
    daily_rf = align_rf_to_dates(portfolio_returns.index, rf_data).reset_index(drop=True)
    excess_returns = portfolio_returns.reset_index(drop=True) - daily_rf
    excess_std = excess_returns.std(ddof=1)
    if pd.notna(excess_std) and excess_std > 0:
        sharpe_ratio = excess_returns.mean() / excess_std * np.sqrt(365.0)
    else:
        sharpe_ratio = np.nan

    running_max = portfolio_value.cummax()
    drawdown = portfolio_value / running_max - 1.0
    max_drawdown = float(drawdown.min())

    return {
        'Portfolio': portfolio_name,
        'Members': ', '.join(members),
        'Number_of_Skins': number_of_skins,
        'Start_Date': actual_start_date.strftime('%Y-%m-%d'),
        'End_Date': actual_end_date.strftime('%Y-%m-%d'),
        'Total_Return': total_return,
        'Annualized_Return': annualized_return,
        'Annualized_Volatility': annualized_volatility,
        'Sharpe_Ratio': sharpe_ratio,
        'Max_Drawdown': max_drawdown,
        'Observations': len(portfolio_returns),
        'Gross_Return_Note': (
            'Price return before Steam fees, bid-ask spread, slippage, and taxes. '
            'Cumulative portfolio returns use common universe-wide start/end dates; '
            'intermediate one-day return observations use available constituent data '
            'without forward-filling.'
        ),
    }


def calculate_spread_metrics(feature, split_value, spread_returns):
    if spread_returns.empty:
        return {'Portfolio': f'High-Low {feature}', 'Feature': feature, 'Split_Value': split_value}
    spread_std = spread_returns.std(ddof=1)
    annualized_spread = spread_returns.mean() * 365.0
    annualized_volatility = spread_std * np.sqrt(365.0)
    if pd.notna(spread_std) and spread_std > 0:
        sharpe = spread_returns.mean() / spread_std * np.sqrt(365.0)
    else:
        sharpe = np.nan
    return {'Portfolio': f'High-Low {feature}', 'Feature': feature, 'Split_Value': split_value, 'Members': 'Descriptive high-minus-low spread', 'Number_of_Skins': np.nan, 'Start_Date': str(spread_returns.index[0].date()), 'End_Date': str(spread_returns.index[-1].date()), 'Total_Return': np.nan, 'Annualized_Return': annualized_spread, 'Annualized_Volatility': annualized_volatility, 'Sharpe_Ratio': sharpe, 'Max_Drawdown': np.nan, 'Observations': len(spread_returns), 'Gross_Return_Note': 'Annualized_Return is the average daily high-minus-low return differential multiplied by 365. This is a descriptive factor spread, not a compounded investable portfolio and is not assumed directly shortable.'}


def build_visual_portfolios(master, price_data, rf_data):
    """Build all factor portfolios using common universe-wide endpoints."""
    rows = []
    benchmark_members = master['Market_Name'].dropna().drop_duplicates().tolist()
    common_start, common_end = get_common_portfolio_period(price_data, benchmark_members)
    if common_start is None or common_end is None:
        raise RuntimeError(
            'Could not identify at least two dates with observed prices for every '
            'skin in the portfolio universe.'
        )

    print(
        f'Common portfolio endpoints: {common_start.date()} to {common_end.date()} '
        f'(no forward-filling)'
    )

    benchmark = portfolio_metrics(
        price_data, benchmark_members, rf_data, 'Spectrum 2 Benchmark',
        start_date=common_start, end_date=common_end
    )
    if benchmark is not None:
        benchmark['Feature'] = 'Benchmark'
        benchmark['Split_Value'] = np.nan
        rows.append(benchmark)

    for feature in PORTFOLIO_FEATURES:
        if feature not in master.columns:
            continue
        feature_data = master[['Market_Name', feature]].dropna()
        if len(feature_data) < 2:
            continue

        median_value = feature_data[feature].median()
        high_members = feature_data.loc[
            feature_data[feature] >= median_value, 'Market_Name'
        ].tolist()
        low_members = feature_data.loc[
            feature_data[feature] < median_value, 'Market_Name'
        ].tolist()

        high_metrics = portfolio_metrics(
            price_data, high_members, rf_data, f'High {feature}',
            start_date=common_start, end_date=common_end
        )
        low_metrics = portfolio_metrics(
            price_data, low_members, rf_data, f'Low {feature}',
            start_date=common_start, end_date=common_end
        )

        if high_metrics is not None:
            high_metrics['Feature'] = feature
            high_metrics['Split_Value'] = median_value
            rows.append(high_metrics)
        if low_metrics is not None:
            low_metrics['Feature'] = feature
            low_metrics['Split_Value'] = median_value
            rows.append(low_metrics)

        if high_metrics is not None and low_metrics is not None:
            high_series = get_portfolio_return_series(
                price_data, high_members, common_start, common_end
            )
            low_series = get_portfolio_return_series(
                price_data, low_members, common_start, common_end
            )
            spread = pd.concat(
                [
                    high_series.rename('Portfolio_Return_High'),
                    low_series.rename('Portfolio_Return_Low'),
                ],
                axis=1,
                join='inner',
            ).dropna()
            if not spread.empty:
                spread_return = (
                    spread['Portfolio_Return_High'] - spread['Portfolio_Return_Low']
                ).rename('High_Minus_Low_Return')
                rows.append(calculate_spread_metrics(feature, median_value, spread_return))

    return pd.DataFrame(rows)

def short_skin_name(market_name_value):
    """Remove the wear suffix from chart labels."""
    return str(market_name_value).replace(' (Factory New)', '')


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(IMAGE_DIR, exist_ok=True)

    print()
    print('=' * 70)
    print('CS2 SPECTRUM 2 FINANCE + VISUAL RESEARCH PROJECT')
    print('=' * 70)
    print()
    print('STEP 1: GETTING CURRENT MARKET DATA')
    print('-' * 70)
    current_data = get_current_market_data()
    current_prices = extract_current_prices(current_data)
    current_prices.to_csv(os.path.join(OUTPUT_DIR, 'spectrum2_current_prices.csv'), index=False)
    print(f'Current-price rows collected: {len(current_prices)}')
    print()
    print('STEP 2: DOWNLOADING IMAGES + ANALYZING COLORS')
    print('-' * 70)
    visual_data = get_visual_data(current_prices)
    visual_data.to_csv(os.path.join(OUTPUT_DIR, 'spectrum2_visual_features.csv'), index=False)
    print(f'Visual rows collected: {len(visual_data)}')
    print()
    print('STEP 3: GETTING THREE YEARS OF PRICE HISTORY')
    print('-' * 70)
    history_response = get_history()
    history_df = history_to_dataframe(history_response)
    history_df.to_csv(os.path.join(OUTPUT_DIR, 'spectrum2_daily_prices.csv'), index=False)
    print(f'Historical price rows collected: {len(history_df)}')
    print()
    print('STEP 4: GETTING HISTORICAL RISK-FREE RATES')
    print('-' * 70)
    rf_data = get_risk_free_rates(history_df['Date'].min(), history_df['Date'].max())
    rf_data.to_csv(os.path.join(OUTPUT_DIR, 'spectrum2_risk_free_rates.csv'), index=False)
    print(f'Risk-free observations collected: {len(rf_data)}')
    print()
    print('STEP 5: CALCULATING FINANCIAL METRICS')
    print('-' * 70)
    metrics = calculate_metrics(history_df, rf_data)
    metrics.to_csv(os.path.join(OUTPUT_DIR, 'spectrum2_financial_metrics.csv'), index=False)
    print(f'Financial metric rows: {len(metrics)}')
    print()
    print('STEP 6: CALCULATING DAILY RETURNS')
    print('-' * 70)
    daily_returns = make_daily_return_data(history_df, rf_data)
    daily_returns.to_csv(os.path.join(OUTPUT_DIR, 'spectrum2_daily_returns.csv'), index=False)
    print(f'Daily return rows: {len(daily_returns)}')
    print()
    print('STEP 6B: ROBUSTNESS CHECK — WINSORIZED DAILY RETURNS')
    print('-' * 70)
    winsorized_returns, winsor_lower, winsor_upper = winsorize_daily_returns(
        daily_returns, WINSOR_LOWER_QUANTILE, WINSOR_UPPER_QUANTILE
    )
    winsorized_returns.to_csv(
        os.path.join(OUTPUT_DIR, 'spectrum2_daily_returns_winsorized.csv'), index=False
    )
    winsorized_metrics = calculate_winsorized_metrics(winsorized_returns)
    winsorized_metrics.to_csv(
        os.path.join(OUTPUT_DIR, 'spectrum2_financial_metrics_winsorized.csv'), index=False
    )
    robustness_summary, robustness_comparison = make_robustness_summary(
        metrics, winsorized_metrics, winsor_lower, winsor_upper, winsorized_returns
    )
    robustness_summary.to_csv(
        os.path.join(OUTPUT_DIR, 'spectrum2_robustness_summary.csv'), index=False
    )
    robustness_comparison.to_csv(
        os.path.join(OUTPUT_DIR, 'spectrum2_robustness_metric_comparison.csv'), index=False
    )
    print(robustness_summary.to_string(index=False))
    print()
    print('STEP 7: BUILDING MASTER DATASET')
    print('-' * 70)
    master = visual_data.merge(metrics, on='Market_Name', how='outer')
    master = master.merge(current_prices.drop(columns=['Icon_URL'], errors='ignore'), on='Market_Name', how='left', suffixes=('', '_Current'))
    master = add_skin_metadata(master)
    master.to_csv(os.path.join(OUTPUT_DIR, 'spectrum2_master.csv'), index=False)
    print(f'Master dataset rows: {len(master)}')
    print()
    print('STEP 8: CALCULATING VISUAL / FINANCIAL CORRELATIONS')
    print('-' * 70)
    correlations = make_correlation_table(master)
    correlations.to_csv(os.path.join(OUTPUT_DIR, 'spectrum2_correlations.csv'), index=False)
    print(correlations.to_string(index=False))
    print()
    print('STEP 8B: ROBUSTNESS CORRELATIONS')
    print('-' * 70)
    robustness_master = visual_data.merge(winsorized_metrics, on='Market_Name', how='outer')
    robustness_master = add_skin_metadata(robustness_master)
    robustness_master.to_csv(
        os.path.join(OUTPUT_DIR, 'spectrum2_master_winsorized.csv'), index=False
    )
    robustness_correlations = make_correlation_table(robustness_master)
    robustness_correlations.to_csv(
        os.path.join(OUTPUT_DIR, 'spectrum2_correlations_winsorized.csv'), index=False
    )
    print(robustness_correlations.to_string(index=False))
    print()
    print('STEP 9: BUILDING VISUAL FACTOR PORTFOLIOS')
    print('-' * 70)
    portfolios = build_visual_portfolios(master, daily_returns, rf_data)
    portfolios.to_csv(os.path.join(OUTPUT_DIR, 'spectrum2_portfolios.csv'), index=False)
    if not portfolios.empty:
        print(portfolios[['Portfolio', 'Number_of_Skins', 'Total_Return', 'Annualized_Return', 'Annualized_Volatility', 'Sharpe_Ratio', 'Max_Drawdown']].to_string(index=False))
    print()
    print('STEP 9B: ROBUSTNESS FACTOR PORTFOLIOS')
    print('-' * 70)
    winsorized_price_index = make_winsorized_price_index(winsorized_returns)
    robustness_portfolios = build_visual_portfolios(
        robustness_master, winsorized_price_index, rf_data
    )
    robustness_portfolios.to_csv(
        os.path.join(OUTPUT_DIR, 'spectrum2_portfolios_winsorized.csv'), index=False
    )
    if not robustness_portfolios.empty:
        print(robustness_portfolios[['Portfolio', 'Number_of_Skins', 'Total_Return', 'Annualized_Return', 'Annualized_Volatility', 'Sharpe_Ratio', 'Max_Drawdown']].to_string(index=False))
    print()
    print('=' * 70)
    print('DONE')
    print('=' * 70)
    print()
    print('Files saved in:')
    print(f'  {OUTPUT_DIR}/')
    print()
    print('Main file:')
    print('  spectrum2_master.csv')
    print()
    print('Other data:')
    print('  spectrum2_current_prices.csv')
    print('  spectrum2_visual_features.csv')
    print('  spectrum2_daily_prices.csv')
    print('  spectrum2_daily_returns.csv')
    print('  spectrum2_financial_metrics.csv')
    print('  spectrum2_correlations.csv')
    print('  spectrum2_portfolios.csv')
    print('  spectrum2_risk_free_rates.csv')
    print('  spectrum2_daily_returns_winsorized.csv')
    print('  spectrum2_financial_metrics_winsorized.csv')
    print('  spectrum2_master_winsorized.csv')
    print('  spectrum2_correlations_winsorized.csv')
    print('  spectrum2_portfolios_winsorized.csv')
    print('  spectrum2_robustness_summary.csv')
    print('  spectrum2_robustness_metric_comparison.csv')
    print()
if __name__ == '__main__':
    main()
