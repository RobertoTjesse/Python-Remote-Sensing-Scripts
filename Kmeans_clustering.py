# -*- coding: utf-8 -*-
"""
K-means clustering using Sentinel-1 and -2 data

- Use the SentinelHub package and account to download atmospherically
  corrected Sentinel-2 and Sentinel-1 to the python session.

- Apply K-Mean clustering in iterative mode. Select the final number of
  clusters accordingly to the silhouette score.

- Apply pre-processing functions, such as PCA transformation and Brightness
  Normalization.

Created on Thu Aug 16 14:26:23 2018

@author: Javier Lopatin | javier.lopatin@kit.edu
"""

import numpy as np
import rasterio, rasterio.mask, fiona
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.decomposition import PCA
import matplotlib.pyplot as plt
from sentinelhub import WmsRequest, MimeType, CRS, BBox, CustomUrlParam, geo_utils, DataSource

################################
### functions

def plot_image(image, factor=1):
    """
    Utility function for plotting RGB images.
    """
    plt.subplots(nrows=1, ncols=1, figsize=(15, 7))

    if np.issubdtype(image.dtype, np.floating):
        plt.imshow(np.minimum(image * factor, 1))
    else:
        plt.imshow(image)


def run_Kmeans(raster, numSamples=10000, bnorm=False, pca=False, n_jobs=-2):
    """
    select n number of pixeles to perform the clustering analysis
    first, reshape image to be (rows*columns, bands)

    Parameters:
    - numSamples: number of random samples taken to train the cluster. Default = 10000
    - bnorm: apply Brightness normalization to the data
    - pca: apply principal component transformation to the data
    - n_jobs: number of CPU cores to use. Default: all - 2

    """
    X = np.reshape(raster, (rows*columns, raster.shape[2]))

    # if brightness normalization
    if bnorm == True:
        def norm(r):
            norm = r / np.sqrt( np.sum((r**2), 0) )
            return norm
        X = np.apply_along_axis(norm, 0, X)

    # if pca
    if pca == True:
        X = PCA(n_components=X.shape[1]).fit_transform(X)

    # select pixels
    idx = np.random.randint(X.shape[0], size=numSamples)
    samples = X[idx, :]

    ###############
    ### fit K-means

    # select a suitable number of clusters according to silhouette_score
    range_n_clusters = range(2, 33, 2)

    for n_clusters in range_n_clusters:
        clusterer = KMeans(n_clusters = n_clusters, random_state=10, n_jobs=n_jobs)
        cluster_labels = clusterer.fit_predict(samples)
        silhouette = silhouette_score(samples, cluster_labels)
        print("For n_clusters =", n_clusters,
              "The average silhouette_score is:", silhouette)

    """

    Stop!!! ask for the best n_Clusters to be used. Enter the number in the terminal

    """
    bestCluster = input("Please enter your selected number of clusters: ")

    # run KMeans one last time using the selected number of clusters
    kmeans = KMeans(n_clusters = int(bestCluster), random_state=123, n_jobs=n_jobs)
    cluster_labels = kmeans.fit_predict(samples)
    silhouette = silhouette_score(samples, cluster_labels)
    predCluster = kmeans.predict(X)

    # reshape prediction to shape (rows, columns)
    predCluster = np.reshape(predCluster, (rows, columns))

    # save kmeans clustering as:
    output = "Sentinel_40m_kmeans_"+bestCluster+"k.tif"
    if bnorm == True:
        output = output[:-4] + "_bnorm.tif"
    if pca == True:
        output = output[:-4] + "_pca.tif"

    # Update meta to reflect the number of layers; add dtype
    meta.update(dtype=str(predCluster.dtype), count = 1)

    # save cluster to disk
    with rasterio.open(output, 'w', **meta) as dst:
        dst.write(predCluster, 1)

    return(predCluster)

######################################
### END FUNCTIONS

if __name__ == "__main__":


    """

    Load Sentinel-1 and -1 images from SentinelHub
    We selected 20m of spatial resolution for speed.

    """

    # this is a personal code number. You need to add your own to work
    INSTANCE_ID = '7748e676-f55c-4843-900b-1d3e2962a7f1'

    # define study area.
    # coordinate system is (longitude and latitude coordinates of upper left and lower right corners)
    cauquenes_coords_wgs84 = [-72.802, -35.653, -72.030, -36.320]
    cauquenes_bbox = BBox(bbox=cauquenes_coords_wgs84, crs=CRS.WGS84)

    # check for pixels sizes to download the images
    """
    20m: width=3570, height=3600
    """
    geo_utils.bbox_to_resolution(cauquenes_bbox, 1570, 1600)

    ########################################################
    ### Sentinel-2

    # check for the last available S-2 image with less than 30% cloud cover
    # only in RGB color for visualization
    wms_true_color_request = WmsRequest(layer='TRUE-COLOR-S2-L1C',
                                        bbox=cauquenes_bbox,
                                        time=('2017-12-01', '2017-12-31'),
                                        maxcc=0.2,
                                        width=3570, height=3600,
                                        instance_id=INSTANCE_ID)
    # get all images to python session
    wms_true_color_img = wms_true_color_request.get_data()

    print('These %d images were taken on the following dates:' % len(wms_true_color_img))
    for index, date in enumerate(wms_true_color_request.get_dates()):
        print(' - image %d was taken on %s' % (index, date))

    # see images one by one
    plot_image(wms_true_color_img[1])

    # Download raw bands of the selected image with 20m pixel size
    wms_bands_request = WmsRequest(data_folder='test_dir_tiff',
                                   layer='BANDS-S2-L1C',
                                   bbox=cauquenes_bbox,
                                   time='2017-12-10',
                                   width=1570, height=1600,
                                   image_format=MimeType.TIFF_d32f,
                                   instance_id=INSTANCE_ID,
                                   custom_url_params={CustomUrlParam.ATMFILTER: 'ATMCOR'})
    # save image to disk just in case
    wms_bands_img = wms_bands_request.save_data()
    # load aimage to python session
    wms_bands_img = wms_bands_request.get_data()
    # see image
    plot_image(wms_bands_img[-1])

    ########################################################
    ### Sentinel-2

    ### Sentinel-1 IW polyrization. Request RGB for visualizaation
    s1_request = WmsRequest(data_source=DataSource.SENTINEL1_IW,
                            layer='TRUE-COLOR-S1-IW',
                            bbox=cauquenes_bbox,
                            time=('2017-12-05', '2017-12-15'),
                            width=1190, height=1200,
                            instance_id=INSTANCE_ID)
    # get data to python session
    s1_data = s1_request.get_data()

    print('These %d images were taken on the following dates:' % len(s1_data))
    for index, date in enumerate(s1_request.get_dates()):
        print(' - image %d was taken on %s' % (index, date))

    # plot images one by one
    plot_image(s1_data[2])

    # dowload raw bands of the selected image with 20m pixel size
    s1_request = WmsRequest(data_folder='test_dir_tiff',
                            data_source=DataSource.SENTINEL1_IW,
                            layer='BANDS-S1-IW',
                            bbox=cauquenes_bbox,
                            time='2017-12-12',
                            width=1570, height=1600,
                            image_format=MimeType.TIFF_d32f,
                            instance_id=INSTANCE_ID)
    # load data to python session
    s1_data = s1_request.save_data()

    #######################################################
    ### Analysis

    # import raster. You also can use directly the loaded images from SentinelHub
    S2 = "test_dir_tiff/S2_40m.tiff"
    S1 = "test_dir_tiff/S1_40m_IW.tiff"
    shp = "shapefile.shp" # study area to crop the images

    # load shapefile geometry
    with fiona.open(shp, "r") as shapefile:
        features = [feature["geometry"] for feature in shapefile]

    # open and crop S2
    with rasterio.open(S2) as src:
        img, transform = rasterio.mask.mask(src, features, crop=True)
        meta = src.meta.copy() # save metadata info
        meta.update({"driver": "GTiff", # update metadata geometry to the croped version
                     "height": img.shape[1],
                     "width": img.shape[2],
                     "transform": transform})
        baseName = src.name # raster name
        bands, rows, columns = img.shape # raster size

    # open and crop S1. Metadata not needed, same specifications as S2
    with rasterio.open(S1) as src:
        img2, transform = rasterio.mask.mask(src, features, crop=True)

    # stack S2 and S1 images
    raster = np.concatenate((img, img2), axis=0)
    # vosualize stacked raster
    plot_image(raster[:,:,[8,4,3]])

    # transpose raster to shape (rows, columns, bands)
    raster = np.transpose(raster, [1,2,0])

    ##############################################################
    ### run K-means with differing pre-processing transformations

    # KMeans with raw data
    kmeans1 = run_Kmeans(raster)
    plot_image(kmeans2)

    # KMeans with PCA transformaiton
    kmeans2 = run_Kmeans(raster, pca=True)
    plot_image(kmeans2)

    # KMeans with brightness normalization
    kmeans3 = run_Kmeans(raster, bnorm=True)
    plot_image(kmeans3)

    # KMeans with brightness normalization and PCA transformaiton 
    kmeans4 = run_Kmeans(raster, bnorm=True, pca=True)
    plot_image(kmeans4)
