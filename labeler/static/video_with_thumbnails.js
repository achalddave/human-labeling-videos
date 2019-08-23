// Modified from VGG VIA: https://gitlab.com/vgg/via/
class SingleVideoThumbnailCreator {
  constructor(videoSrc) {
    this.videoSrc = videoSrc;
    this.fwidth = 160;
    this.thumbnails = {};

    // state
    this.is_thumbnail_read_ongoing = false;
    this.thumbnail_time = 0;
    this.thumbnail_canvas = document.createElement("canvas");
  }

  load() {
    return new Promise(
      function(ok_callback, err_callback) {
        this._load_video().then(
          function() {
            this.video.currentTime = 0.0;
            ok_callback();
          }.bind(this),
          function(load_err) {
            console.log(load_err);
            err_callback();
          }.bind(this)
        );
      }.bind(this)
    );
  }

  _load_video() {
    return new Promise(
      function(ok_callback, err_callback) {
        this.video = document.createElement("video");
        this.video.setAttribute("src", this.videoSrc);
        this.video.setAttribute("preload", "auto");

        this.video.addEventListener(
          "loadeddata",
          function() {
            let aspect_ratio = this.video.videoHeight / this.video.videoWidth;
            this.fheight = Math.floor(this.fwidth * aspect_ratio);
            this.thumbnail_canvas.width = this.fwidth;
            this.thumbnail_canvas.height = this.fheight;
            this.thumbnail_context = this.thumbnail_canvas.getContext("2d", {
              alpha: false
            });
            ok_callback();
          }.bind(this)
        );

        this.video.addEventListener(
          "error",
          function() {
            err_callback("error");
          }.bind(this)
        );
        this.video.addEventListener(
          "abort",
          function() {
            err_callback("abort");
          }.bind(this)
        );

        this.video.addEventListener("seeked", this._on_seeked.bind(this));
      }.bind(this)
    );
  }

  get_thumbnail(time_float) {
    this.is_thumbnail_read_ongoing = true;
    this.thumbnail_time = parseInt(time_float);
    this.video.currentTime = this.thumbnail_time;
    return new Promise((ok_callback) => {
      this._thumbnail_generated_callback = ok_callback;
    });
  }

  _on_seeked() {
    if (this.is_thumbnail_read_ongoing && this.thumbnail_context) {
      this.is_thumbnail_read_ongoing = false;
      this.thumbnail_context.drawImage(
        this.video,
        0,
        0,
        this.video.videoWidth,
        this.video.videoHeight,
        0,
        0,
        this.fwidth,
        this.fheight
      );
      this._thumbnail_generated_callback();
    }
  }
}

class ThumbnailCreator {
  constructor() {
    // Contains container ids for which thumbnails have been generated.
    this.thumbnailsGenerated = {};
  }

  createContainerThumbnails(labelContainer) {
    let containerId = labelContainer.attr("id");

    let thumbnailContainer = labelContainer.find(
      ".to-label-thumbnails-container"
    );

    if (this.thumbnailsGenerated.hasOwnProperty(containerId)) {
      return;
    }

    let video = labelContainer.find("video.to-label");
    let numThumbnails = parseInt(thumbnailContainer.attr("data-num-thumbnails"));
    let requireFirstThumbnail =
      JSON.parse(thumbnailContainer.attr("data-require-first-thumbnail"));

    let creator = new SingleVideoThumbnailCreator(video.attr("src"));

    return new Promise((ok_callback, err_callback) => {
      creator.load().then(() => {
        let duration = creator.video.duration;
        let promise = Promise.resolve();
        for (let i = 1; i < numThumbnails + 1; ++i) {
          let thumbnailTime = (duration * i) / numThumbnails;
          if (requireFirstThumbnail && i == 1) {
            thumbnailTime = 0;
          }

          // Next promise will be resolved after this thumbnail is received.
          promise = promise.then(() => {
            return creator.get_thumbnail(thumbnailTime);
          });

          promise = promise.then(() => {
            let previewCanvas = creator.thumbnail_canvas;
            let thumbnailCanvas = $("<canvas>")[0];
            thumbnailCanvas.width = previewCanvas.width;
            thumbnailCanvas.height = previewCanvas.height;
            thumbnailCanvas.getContext("2d").drawImage(previewCanvas, 0, 0);
            let canvasContainer = $(
              "<div class='thumbnail-canvas-container'></div>"
            );
            canvasContainer.append(thumbnailCanvas);
            thumbnailContainer.append(canvasContainer);
          });
        }
        this.thumbnailsGenerated[containerId] = true;
        promise.then(() => {
          ok_callback();
        }).catch(err_callback);
      });
    })
  }

  showThumbnails() {
    // Hide all other thumbnails
    $(".to-label-thumbnails-container").hide();
    $(".active").find(".to-label-thumbnails-container").show();
  }
}

let thumbnailer = new ThumbnailCreator();
$(function() {
  let thumbnailPromise = Promise.resolve();
  $(".data-label-container").each(function() {
    thumbnailPromise = thumbnailPromise.then(() => {
      thumbnailer.createContainerThumbnails($(this));
    });
  });
});

window.addEventListener(
  "activeContainerUpdated",
  thumbnailer.showThumbnails.bind(thumbnailer)
);
