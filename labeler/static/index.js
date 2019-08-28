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
  var elementMid = container.offset().top + container.height() / 2;
  $([document.documentElement, document.body]).animate({
    scrollTop: Math.max(0,
      elementMid - ($(window).height() / 2))
  }, 100);
}

$(function() {
  // var topSpace = 5;
  $('#preview-container').hide();

  $('video.to-label').each(function() {
    this.playbackRate = 2.0;
  })

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
    } else {
      var labelObjects = $('.active').find('input.keyboard-' + event.key);
      if (labelObjects.length != 0) {
        console.log(labelObjects.length);
        labelObjects.prop('checked', !labelObjects.prop('checked'));
      } else {
        let newEvent = new CustomEvent('unhandledKey', { detail: event});
        window.dispatchEvent(newEvent);
      }
    }
  });

  $("label").keypress(function(event) {
    if (event.which == 32) { // space bar
      $(this).click();
      event.preventDefault();
    }
  });

  $('form').submit(function() {
    var error = false;
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

  var addedHandler = false;
  $('.to-label-container img, .to-label-container .thumbnail').click(function() {
    var preview = $('#preview'),
        container = $('#preview-container');
    if (!addedHandler) {
      container.click(function() {
        container.hide();
      });
      addedHandler = true;
    }
    var currentSrc = $(this).attr('src');
    if (preview.is(':visible') && preview.attr('src') == currentSrc) {
      container.hide();
    } else {
      container.show();
      preview.attr('src', currentSrc).show();
      preview.css({ margin: "0 auto" });
      // if (preview.height() > 0.9 * $(window).height()) {
      //   // preview.css({'width': 'auto', 'height': '90%'});
      //   var space = ($(window).width() - preview.width()) / 2;
      //   preview.css({'left': space.toString() + 'px'});
      // } else {
      //   var space = ($(window).height() - preview.height()) / 2;
      //   preview.css({'top': space.toString() + 'px'});
      // }
    }
  });

  $('#preview').click(() => $(this).hide());
});
