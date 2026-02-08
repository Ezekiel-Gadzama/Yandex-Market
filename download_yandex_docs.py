#!/usr/bin/env python3
"""
Script to download Yandex Market Partner API documentation pages
and save them to .cursor/rules folder for Cursor AI to use.

Requires: beautifulsoup4
Install with: pip install beautifulsoup4
"""

import os
import re
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
import time

try:
    from bs4 import BeautifulSoup
except ImportError:
    print("Error: beautifulsoup4 is required. Install it with: pip install beautifulsoup4")
    exit(1)

# List of Yandex documentation URLs (English versions)
YANDEX_DOCS_URLS = [
    # Main Documentation (1-15)
    "https://yandex.ru/dev/market/partner-api/doc/en/",
    "https://yandex.ru/dev/market/partner-api/doc/en/concepts/authorization",
    "https://yandex.ru/dev/market/partner-api/doc/en/concepts/api-key",
    "https://yandex.ru/dev/market/partner-api/doc/en/concepts/access",
    "https://yandex.ru/dev/market/partner-api/doc/en/_auto/scopes_summary/pages/inventory-and-order-processing",
    "https://yandex.ru/dev/market/partner-api/doc/en/_auto/scopes_summary/pages/inventory-and-order-processing_read-only",
    "https://yandex.ru/dev/market/partner-api/doc/en/_auto/scopes_summary/pages/pricing",
    "https://yandex.ru/dev/market/partner-api/doc/en/_auto/scopes_summary/pages/pricing_read-only",
    "https://yandex.ru/dev/market/partner-api/doc/en/_auto/scopes_summary/pages/offers-and-cards-management",
    "https://yandex.ru/dev/market/partner-api/doc/en/_auto/scopes_summary/pages/offers-and-cards-management_read-only",
    "https://yandex.ru/dev/market/partner-api/doc/en/_auto/scopes_summary/pages/promotion",
    "https://yandex.ru/dev/market/partner-api/doc/en/_auto/scopes_summary/pages/promotion_read-only",
    "https://yandex.ru/dev/market/partner-api/doc/en/_auto/scopes_summary/pages/finance-and-accounting",
    "https://yandex.ru/dev/market/partner-api/doc/en/_auto/scopes_summary/pages/communication",
    "https://yandex.ru/dev/market/partner-api/doc/en/_auto/scopes_summary/pages/supplies-management_read-only",
    
    # Core Concepts (16-30)
    "https://yandex.ru/dev/market/partner-api/doc/en/concepts/oauth-2.0",
    "https://yandex.ru/dev/market/partner-api/doc/en/concepts/method-call",
    "https://yandex.ru/dev/market/partner-api/doc/en/concepts/input-format",
    "https://yandex.ru/dev/market/partner-api/doc/en/concepts/result-format",
    "https://yandex.ru/dev/market/partner-api/doc/en/concepts/error-codes",
    "https://yandex.ru/dev/market/partner-api/doc/en/concepts/limits",
    "https://yandex.ru/dev/market/partner-api/doc/en/concepts/pagination",
    "https://yandex.ru/dev/market/partner-api/doc/en/concepts/debug",
    "https://yandex.ru/dev/market/partner-api/doc/en/concepts/sandbox",
    "https://yandex.ru/dev/market/partner-api/doc/en/console",
    "https://yandex.ru/dev/market/partner-api/doc/en/concepts/api-access",
    "https://yandex.ru/dev/market/partner-api/doc/en/concepts/integration-signing",
    "https://yandex.ru/dev/market/partner-api/doc/en/concepts/openapi",
    "https://yandex.ru/dev/market/partner-api/doc/en/concepts/best-practices",
    "https://yandex.ru/dev/market/partner-api/doc/en/market-yandex-go-sellers",
    
    # Step-by-Step Guides (31-54)
    "https://yandex.ru/dev/market/partner-api/doc/en/step-by-step/quick-start-js",
    "https://yandex.ru/dev/market/partner-api/doc/en/step-by-step/assortment-add-goods",
    "https://yandex.ru/dev/market/partner-api/doc/en/step-by-step/content-change",
    "https://yandex.ru/dev/market/partner-api/doc/en/step-by-step/recommendations",
    "https://yandex.ru/dev/market/partner-api/doc/en/step-by-step/assortment-archive",
    "https://yandex.ru/dev/market/partner-api/doc/en/step-by-step/stocks",
    "https://yandex.ru/dev/market/partner-api/doc/en/step-by-step/assortment-change-prices",
    "https://yandex.ru/dev/market/partner-api/doc/en/step-by-step/promos",
    "https://yandex.ru/dev/market/partner-api/doc/en/step-by-step/orders-receive",
    "https://yandex.ru/dev/market/partner-api/doc/en/step-by-step/fbs",
    "https://yandex.ru/dev/market/partner-api/doc/en/step-by-step/express",
    "https://yandex.ru/dev/market/partner-api/doc/en/concepts/dbs-order-status-model",
    "https://yandex.ru/dev/market/partner-api/doc/en/step-by-step/digital",
    "https://yandex.ru/dev/market/partner-api/doc/en/step-by-step/business-info",
    "https://yandex.ru/dev/market/partner-api/doc/en/step-by-step/supplies",
    "https://yandex.ru/dev/market/partner-api/doc/en/step-by-step/fby-fbs-express-return-status-model",
    "https://yandex.ru/dev/market/partner-api/doc/en/step-by-step/dbs-return-status-model",
    "https://yandex.ru/dev/market/partner-api/doc/en/step-by-step/reports",
    "https://yandex.ru/dev/market/partner-api/doc/en/step-by-step/goods-feedback",
    "https://yandex.ru/dev/market/partner-api/doc/en/step-by-step/goods-questions",
    "https://yandex.ru/dev/market/partner-api/doc/en/step-by-step/boost",
    "https://yandex.ru/dev/market/partner-api/doc/en/step-by-step/ratings",
    "https://yandex.ru/dev/market/partner-api/doc/en/step-by-step/chats",
    "https://yandex.ru/dev/market/partner-api/doc/en/step-by-step/warehouses",
    
    # Overview (55-63)
    "https://yandex.ru/dev/market/partner-api/doc/en/overview/",
    "https://yandex.ru/dev/market/partner-api/doc/en/overview/business",
    "https://yandex.ru/dev/market/partner-api/doc/en/overview/fby",
    "https://yandex.ru/dev/market/partner-api/doc/en/overview/fbs",
    "https://yandex.ru/dev/market/partner-api/doc/en/overview/express",
    "https://yandex.ru/dev/market/partner-api/doc/en/overview/dbs",
    "https://yandex.ru/dev/market/partner-api/doc/en/overview/comparison",
    "https://yandex.ru/dev/market/partner-api/doc/en/changelog/main",
    "https://yandex.ru/dev/market/partner-api/doc/en/changelog/deprecated",
    
    # API Reference - Campaigns (64-65)
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/campaigns/getCampaigns",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/campaigns/getCampaign",
    
    # API Reference - Business Settings (66)
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/businesses/getBusinessSettings",
    
    # API Reference - Categories (67-68)
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/categories/getCategoriesTree",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/content/getCategoryContentParameters",
    
    # API Reference - Assortment & Offers (69-83)
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/business-assortment/updateOfferMappings",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/assortment/updateCampaignOffers",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/business-offer-mappings/generateOfferBarcodes",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/reports/generateBarcodesReport",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/content/getOfferCardsContentStatus",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/content/updateOfferContent",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/business-assortment/getOfferMappings",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/assortment/getCampaignOffers",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/business-assortment/deleteOffers",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/assortment/deleteCampaignOffers",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/assortment/getHiddenOffers",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/assortment/addHiddenOffers",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/assortment/deleteHiddenOffers",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/business-assortment/addOffersToArchive",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/business-assortment/deleteOffersFromArchive",
    
    # API Reference - Stocks & Prices (84-94)
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/stocks/getStocks",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/stocks/updateStocks",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/business-assortment/updateBusinessPrices",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/assortment/updatePrices",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/prices/getDefaultPrices",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/assortment/getPricesByOfferIds",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/business-assortment/getOfferRecommendations",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/business-assortment/getBusinessQuarantineOffers",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/assortment/getCampaignQuarantineOffers",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/business-assortment/confirmBusinessPrices",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/assortment/confirmCampaignPrices",
    
    # API Reference - Promos (95-98)
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/promos/getPromos",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/promos/getPromoOffers",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/promos/updatePromoOffers",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/promos/deletePromoOffers",
    
    # API Reference - Orders (99-113)
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/orders/getBusinessOrders",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/orders/setOrderBoxLayout",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/orders/updateExternalOrderId",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/orders/updateOrderStatus",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/orders/updateOrderStatuses",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/orders/provideOrderItemIdentifiers",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/orders/getOrderIdentifiersStatus",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/orders/verifyOrderEac",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/orders/updateOrderItems",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/orders/setOrderDeliveryTrackCode",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/orders/setOrderDeliveryDate",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/orders/updateOrderStorageLimit",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/orders/getOrderBuyerInfo",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/orders/acceptOrderCancellation",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/orders/provideOrderDigitalCodes",
    
    # API Reference - Order Business Information (114-115)
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/order-business-information/getOrderBusinessBuyerInfo",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/order-business-information/getOrderBusinessDocumentsInfo",
    
    # API Reference - Shipments (116-126)
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/shipments/getShipment",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/shipments/searchShipments",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/shipments/confirmShipment",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/shipments/downloadShipmentReceptionTransferAct",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/shipments/transferOrdersFromShipment",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/shipments/setShipmentPalletsCount",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/shipments/downloadShipmentAct",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/shipments/downloadShipmentDiscrepancyAct",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/shipments/generateShipmentListDocumentReport",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/shipments/downloadShipmentTransportationWaybill",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/shipments/downloadShipmentInboundAct",
    
    # API Reference - Order Labels (127-132)
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/orders/generateOrderLabel",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/orders/generateOrderLabels",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/orders/generateMassOrderLabelsReport",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/orders/getOrderLabelsData",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/shipments/getShipmentOrdersInfo",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/shipments/downloadShipmentPalletLabels",
    
    # API Reference - Supply Requests (133-135)
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/supply-requests/getSupplyRequests",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/supply-requests/getSupplyRequestItems",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/supply-requests/getSupplyRequestDocuments",
    
    # API Reference - Outlets (136-143)
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/outlets/getOutlet",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/outlets/getOutlets",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/outlets/createOutlet",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/outlets/updateOutlet",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/outlets/deleteOutlet",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/outlets/getOutletLicenses",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/outlets/updateOutletLicenses",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/outlets/deleteOutletLicenses",
    
    # API Reference - Returns (144-148)
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/orders/getReturns",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/orders/getReturn",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/orders/getReturnApplication",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/orders/getReturnPhoto",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/orders/submitReturnDecision",
    
    # API Reference - Reports (149-172)
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/reports/generateShowsSalesReport",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/reports/generateSalesGeographyReport",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/reports/generateKeyIndicatorsReport",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/reports/generateCompetitorsPositionReport",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/stats/getOrdersStats",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/reports/generateUnitedOrdersReport",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/reports/generateUnitedReturnsReport",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/assortment/getGoodsStats",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/reports/generateStocksOnWarehousesReport",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/reports/generateGoodsPricesReport",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/reports/generateGoodsFeedbackReport",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/reports/generateGoodsTurnoverReport",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/reports/generateGoodsMovementReport",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/reports/generateJewelryFiscalReport",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/reports/generateGoodsRealizationReport",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/reports/generateUnitedNettingReport",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/reports/generateUnitedMarketplaceServicesReport",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/reports/generateClosureDocumentsReport",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/reports/generateClosureDocumentsDetalizationReport",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/reports/generateShowsBoostReport",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/reports/generateBoostConsolidatedReport",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/reports/generateShelfsStatisticsReport",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/reports/generateBannersStatisticsReport",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/reports/getReportInfo",
    
    # API Reference - Goods Feedback (173-177)
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/goods-feedback/getGoodsFeedbacks",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/goods-feedback/getGoodsFeedbackComments",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/goods-feedback/updateGoodsFeedbackComment",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/goods-feedback/skipGoodsFeedbacksReaction",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/goods-feedback/deleteGoodsFeedbackComment",
    
    # API Reference - Goods Questions (178-180)
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/goods-questions/getGoodsQuestions",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/goods-questions/getGoodsQuestionAnswers",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/goods-questions/updateGoodsQuestionTextEntity",
    
    # API Reference - Bids (181-183)
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/bids/putBidsForBusiness",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/bids/getBidsInfoForBusiness",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/bids/getBidsRecommendations",
    
    # API Reference - Ratings (184-185)
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/ratings/getQualityRatings",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/ratings/getQualityRatingDetails",
    
    # API Reference - Chats (186-192)
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/chats/getChatHistory",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/chats/getChat",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/chats/getChats",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/chats/getChatMessage",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/chats/createChat",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/chats/sendMessageToChat",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/chats/sendFileToChat",
    
    # API Reference - Warehouses (193-195)
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/warehouses/getPagedWarehouses",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/warehouses/updateWarehouseStatus",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/warehouses/getFulfillmentWarehouses",
    
    # API Reference - Authentication (196)
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/auth/getAuthTokenInfo",
    
    # API Reference - Delivery Services (197)
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/orders/getDeliveryServices",
    
    # API Reference - Regions (198-201)
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/regions/getRegionsCodes",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/regions/searchRegionsByName",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/regions/searchRegionsById",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/regions/searchRegionChildren",
    
    # API Reference - Orders (Additional) (202-203)
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/orders/getOrder",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/orders/getOrders",
    
    # API Reference - Offer Mappings (204-208)
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/offer-mappings/updateOfferMappingEntries",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/offer-mappings/getOfferMappingEntries",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/categories/getCategoriesMaxSaleQuantum",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/offer-mappings/getSuggestedOfferMappingEntries",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/business-assortment/getSuggestedOfferMappings",
    
    # API Reference - Prices (209)
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/prices/getPrices",
    
    # API Reference - Orders (Shipment & Returns) (210-211)
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/orders/setOrderShipmentBoxes",
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/orders/setReturnDecision",
    
    # API Reference - Warehouses (Additional) (212)
    "https://yandex.ru/dev/market/partner-api/doc/en/reference/warehouses/getWarehouses",
    
    # Push Notifications (213-217)
    "https://yandex.ru/dev/market/partner-api/doc/en/push-notifications/",
    "https://yandex.ru/dev/market/partner-api/doc/en/push-notifications/concepts/quick-start-notifications-node-express",
    "https://yandex.ru/dev/market/partner-api/doc/en/push-notifications/concepts/data-format",
    "https://yandex.ru/dev/market/partner-api/doc/en/push-notifications/concepts/error-codes",
    "https://yandex.ru/dev/market/partner-api/doc/en/push-notifications/reference/sendNotification",
    
    # Modules (218)
    "https://yandex.ru/dev/market/partner-api/doc/en/modules/1c"
]

# Output folder
OUTPUT_FOLDER = Path(".cursor/rules")

def sanitize_filename(url):
    """Convert URL to a safe filename."""
    parsed = urlparse(url)
    # Get the path and remove leading/trailing slashes
    path = parsed.path.strip('/')
    # Replace slashes with underscores
    filename = path.replace('/', '_') if path else 'index'
    # Add .txt extension
    return f"{filename}.txt"

def extract_documentation_text(html_content):
    """Extract only the documentation text from HTML, removing all markup and scripts.
    Optimized for compact output while maintaining readability."""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Remove script, style, and other non-content elements
    for element in soup(["script", "style", "noscript", "nav", "header", "footer"]):
        element.decompose()
    
    # Find the main content area
    title_elem = soup.find('h1', class_='dc-doc-page-title')
    body_elem = soup.find('div', class_='dc-doc-page__body')
    
    text_parts = []
    last_was_heading = False
    last_was_list = False
    
    # Extract title (compact - no underline)
    if title_elem:
        title_text = title_elem.get_text(strip=True)
        if title_text:
            text_parts.append(title_text)
            last_was_heading = True
    
    # Extract body content with compact formatting
    if body_elem:
        # Process the body element to extract structured text
        for elem in body_elem.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'ul', 'ol', 'li', 'pre', 'code', 'blockquote', 'table', 'tr', 'td', 'th']):
            if elem.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                text = elem.get_text(strip=True)
                if text:
                    # Only add blank line if previous wasn't a heading
                    if not last_was_heading and text_parts:
                        text_parts.append("")
                    text_parts.append(text)
                    last_was_heading = True
                    last_was_list = False
            elif elem.name == 'p':
                text = elem.get_text(strip=True)
                if text:
                    # Join short paragraphs, add line break for longer ones
                    if text_parts and not last_was_heading and not last_was_list:
                        # Check if we can join with previous paragraph
                        prev_text = text_parts[-1] if text_parts else ""
                        if prev_text and len(prev_text) < 100 and len(text) < 100:
                            text_parts[-1] = f"{prev_text} {text}"
                        else:
                            text_parts.append(text)
                    else:
                        text_parts.append(text)
                    last_was_heading = False
                    last_was_list = False
            elif elem.name in ['ul', 'ol']:
                # Lists are handled by their li children
                if not last_was_list and text_parts:
                    text_parts.append("")
                last_was_list = True
            elif elem.name == 'li':
                text = elem.get_text(strip=True)
                if text:
                    # Compact list items
                    text_parts.append(f"• {text}")
                    last_was_heading = False
                    last_was_list = True
            elif elem.name in ['pre', 'code']:
                text = elem.get_text()
                if text.strip():
                    if text_parts:
                        text_parts.append("")
                    text_parts.append(text)
                    last_was_heading = False
                    last_was_list = False
            elif elem.name == 'blockquote':
                text = elem.get_text(strip=True)
                if text:
                    if text_parts:
                        text_parts.append("")
                    text_parts.append(f"Note: {text}")
                    last_was_heading = False
                    last_was_list = False
            elif elem.name == 'table':
                # Handle tables - extract as compact text
                if text_parts:
                    text_parts.append("")
                rows = elem.find_all('tr')
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    if cells:
                        cell_texts = [cell.get_text(strip=True) for cell in cells]
                        text_parts.append(" | ".join(cell_texts))
                last_was_heading = False
                last_was_list = False
        
        # If we didn't get much content, try a simpler extraction
        if len('\n'.join(text_parts)) < 100:
            body_text = body_elem.get_text(separator=' ', strip=True)
            if body_text and len(body_text) > len('\n'.join(text_parts)):
                text_parts = [body_text]
    
    # Clean up the text
    full_text = '\n'.join(text_parts)
    
    # Remove HTML entities
    full_text = full_text.replace('&nbsp;', ' ')
    full_text = full_text.replace('&amp;', '&')
    full_text = full_text.replace('&lt;', '<')
    full_text = full_text.replace('&gt;', '>')
    full_text = full_text.replace('&quot;', '"')
    full_text = full_text.replace('&#x27;', "'")
    
    # Clean up whitespace - remove multiple spaces
    full_text = re.sub(r' +', ' ', full_text)
    
    # Remove excessive blank lines - only allow single blank lines
    full_text = re.sub(r'\n{3,}', '\n\n', full_text)
    
    # Clean up lines - remove trailing spaces and normalize
    lines = full_text.split('\n')
    cleaned_lines = []
    prev_was_blank = False
    
    for line in lines:
        cleaned_line = line.strip()
        # Skip blank lines if previous was also blank
        if not cleaned_line:
            if not prev_was_blank and cleaned_lines:
                cleaned_lines.append("")
                prev_was_blank = True
        else:
            cleaned_lines.append(cleaned_line)
            prev_was_blank = False
    
    full_text = '\n'.join(cleaned_lines)
    
    # Final cleanup - remove leading/trailing blank lines
    full_text = full_text.strip()
    
    # Remove any remaining double blank lines
    full_text = re.sub(r'\n\n\n+', '\n\n', full_text)
    
    return full_text

def download_html(url, output_path):
    """Download HTML content from URL, extract documentation text, and save to file."""
    try:
        print(f"Downloading: {url}")
        
        # Set headers to mimic a browser request
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # Create request with headers
        req = Request(url, headers=headers)
        
        # Make the request
        with urlopen(req, timeout=30) as response:
            # Read and decode the content
            html_content = response.read().decode('utf-8')
            
            # Extract documentation text
            doc_text = extract_documentation_text(html_content)
            
            if not doc_text or len(doc_text.strip()) < 50:
                print(f"⚠ Warning: Extracted text seems too short for {url}")
            
            # Save to file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(doc_text)
        
        print(f"✓ Saved to: {output_path} ({len(doc_text)} characters)")
        return True
        
    except HTTPError as e:
        print(f"✗ HTTP Error {e.code} downloading {url}: {e.reason}")
        return False
    except URLError as e:
        print(f"✗ URL Error downloading {url}: {e.reason}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error with {url}: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main function to download all documentation pages."""
    # Create output folder if it doesn't exist
    OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)
    print(f"Output folder: {OUTPUT_FOLDER.absolute()}\n")
    
    # Download each URL
    success_count = 0
    for url in YANDEX_DOCS_URLS:
        filename = sanitize_filename(url)
        output_path = OUTPUT_FOLDER / filename
        
        if download_html(url, output_path):
            success_count += 1
        
        # Small delay to be respectful to the server
        time.sleep(1)
    
    print(f"\n{'='*60}")
    print(f"Download complete: {success_count}/{len(YANDEX_DOCS_URLS)} files downloaded successfully")
    print(f"Files saved to: {OUTPUT_FOLDER.absolute()}")

if __name__ == "__main__":
    main()
