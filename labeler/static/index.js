function isVisible(elem, partialOk) {
  /* Check if element is in the viewport. Taken from:
    * <https://stackoverflow.com/a/488073/1291812> */
  var docViewTop = $(window).scrollTop();
  var docViewBottom = docViewTop + $(window).height();

  var elemTop = $(elem).offset().top;
  var elemBottom = elemTop + $(elem).height();

  if (!partialOk) {
    return ((elemBottom <= docViewBottom) && (elemTop >= docViewTop));
  } else {
    var aboveViewport = ((elemTop <= docViewTop) &&
                         (elemBottom <= docViewTop));
    var belowViewport = ((elemTop >= docViewBottom) &&
                         (elemBottom >= docViewBottom));
    return !aboveViewport && !belowViewport;
  }
}

function updateContainer(container, updateFocus) {
  updateFocus = updateFocus === undefined ? true : updateFocus;
  $('.active').removeClass('active');
  $(container).addClass('active');
  if (updateFocus) {
    $(container).focus();
  }
  $('video').each(function() { this.pause(); });
  $(container).find('video').each(function() { this.play(); });
  var event = new CustomEvent('activeContainerUpdated');
  window.dispatchEvent(event);
}

function scrollToContainer(container) {
  var elementMid = container.offset().top + container.outerHeight() / 2;
  $([document.documentElement, document.body]).animate({
    scrollTop: Math.max(0,
      elementMid - ($(window).height() / 2))
  }, 100);
}

$(function() {
  // var topSpace = 5;
  $('#preview-container').hide();
  $('body').click(() => $('#preview-container').hide());

  $('video.to-label').each(function() {
    this.playbackRate = 2.0;
  });

  updateContainer($('.data-label-container').eq(0));

  $(".data-label-container").focusin(function() {
    if (!$(this).hasClass("active")) {
      updateContainer($(this), false /*updateFocus*/);
    }
  });

  $(".data-label-container").focus(function() {
    updateContainer($(this), false /*updateFocus*/);
    scrollToContainer($(this));
  });


  $(window).keypress(function(event) {
    if ($('input:text').is(':focus')) {
      return;
    }
    let isOpen = false;
    $("select").each(function() {
      try {
        isOpen = isOpen || $(this).select2("isOpen");
      } catch (e) {}
    })
    if (isOpen) {
      return;
    }

    if(event.keyCode == 13 && (event.metaKey || event.ctrlKey)) {
      $('form').submit();
    }

    if (event.key == 'j' || event.key == 'k') {
      var toSelect;
      if (event.key == 'j') {
        toSelect = $('.active').next('.data-label-container');
        if (toSelect.length == 0) {
          return;
        }
      } else {
        toSelect = $('.active').prev('.data-label-container')
        if (toSelect.length == 0) {
          return;
        }
      }
      scrollToContainer(toSelect);
      updateContainer(toSelect);
      // toSelect.scrollIntoView({'behavior': 'instant'});
    } else if (event.key == 'o') {
      $('.active').find('.to-label').click();  // open preview
    } else if (!isNaN(event.key)) {
      var label_index = parseInt(event.key);
      if (label_index == 0) {
        label_index = 9;
      } else {
        label_index -= 1;
      }
      var labels = $('.active').find('input');
      if (label_index < 0 || label_index >= labels.length) {
        return;
      }
      var label_object = labels.eq(label_index);
      label_object.prop('checked', !label_object.prop('checked'));
    } else if (event.key.match(/^[a-z0-9]+/i)) {
      var labelObjects = $('.active').find('input.keyboard-' + event.key);
      if (labelObjects.length != 0) {
        labelObjects.prop('checked', !labelObjects.prop('checked'));
      }
    } else {
        let newEvent = new CustomEvent('unhandledKey', { detail: event});
        window.dispatchEvent(newEvent);
    }
  });

  $("label").keypress(function(event) {
    if (event.which == 32) { // space bar
      $(this).click();
      event.preventDefault();
    }
  });

  $('form').submit(function() {
    var numUnlabeled = 0;
    $('.labels').each(function(i, labels) {
      if ($(labels).find('input:checked').length == 0) {
        numUnlabeled++;
        $(labels).parent().addClass('container-error');
      } else {
        $(labels).parent().removeClass('container-error');
      }
    });
    if (numUnlabeled > 0) {
      if (numUnlabeled == 1) {
        $('#error').html('One image is unlabeled, please fix.');
      } else {
        $('#error').html(numUnlabeled + ' images unlabeled, please fix.');
      }
      $('#error').show()
      return false;
    } else {
      $('#error').hide();
      return true;
    }
  });

  $('#preview-container').keypress(function(event) {
    let preview = $('#preview');
    if (preview.length == 0 || !preview.is(':visible')) {
      return
    } else if (preview[0].tagName.toLowerCase() == 'video') {
      if (event.key == '.') {
        preview[0].currentTime += 1;
        event.preventDefault();
      } else if (event.key == ',') {
        preview[0].currentTime -= 1;
        event.preventDefault();
      }
    }
  });

  var addedHandler = false;
  $('.to-label, .to-label-container .thumbnail').click(function() {
    var preview = $('#preview'),
        container = $('#preview-container');
    if (!addedHandler) {
      container.click(function() {
        container.hide();
      });
      addedHandler = true;
    }

    var currentSrc = $(this).attr('data-preview') || $(this).attr('src');

    if (
      preview.length > 0 &&
      preview.is(":visible") &&
      preview.attr("src") == currentSrc
    ) {
      container.hide();
    } else {
      container.show();
      let elementType = currentSrc.endsWith('.mp4') && 'video' || 'img';

      if (
        preview.length == 0 ||
        preview[0].tagName.toLowerCase() !== elementType
      ) {
        container.empty();
        if (elementType == "video") {
          preview = $(
            `<video autoplay muted loop controls id="preview"></video>`
          );
        } else {
          preview = $(`<img id="preview"></img>`);
        }
        container.append(preview);
      }
      preview.attr("src", currentSrc).show();
      preview.css({ margin: "0 auto" });
      preview.focus();
      if (elementType == 'video') {
        preview[0].playbackRate = 2;
      }
      // if (preview.height() > 0.9 * $(window).height()) {
      //   // preview.css({'width': 'auto', 'height': '90%'});
      //   var space = ($(window).width() - preview.width()) / 2;
      //   preview.css({'left': space.toString() + 'px'});
      // } else {
      //   var space = ($(window).height() - preview.height()) / 2;
      //   preview.css({'top': space.toString() + 'px'});
      // }
    }
    return false;
  });

  $("#preview").click(function() {
    $(this).hide();
  });
  $("#preview").hide();

  $(".label-search").on("input", function() {
    let text = $(this).val();
    let labels = $(this).closest(".data-label-container").find("label");
    labels.each(function() {
      if ($(this).text().toLowerCase().includes(text.toLowerCase())) {
        $(this).css("opacity", 1);
        // If there is text in the field, allow the label to be tabbed.
        $(this).attr("tabindex", text.length > 0 ? "0" : "-1");
      } else {
        $(this).css("opacity", 0.3);
        $(this).attr("tabindex", "-1");
      }
    });
  });
});
