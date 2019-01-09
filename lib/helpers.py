def generate_image(old_image, new_tag):
    return old_image.rsplit(":")[0] + f":{new_tag}"
