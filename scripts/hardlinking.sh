#!/bin/bash

# Directories
#downloads_dir="/home/$USER"
downloads_dir="/mnt/user/data/downloads"
anime_tv_dir="/mnt/user/data/Media/Anime/TV Series"
anime_movie_dir="/mnt/user/data/Media/Anime/Movies"
light_novel="/mnt/user/data/Media/Books/Light Novels"
music="/mnt/user/data/Media/Music"
video="/mnt/user/data/Media/video"
test="/home/$USER/test_folder_destination"

folders=("$anime_tv_dir" "$anime_movie_dir" "$light_novel" "$music" "$video")

while true; do
	while true; do
		echo "folder in downloads:"
		read folder_name
		if [[ -d "${downloads_dir}/${folder_name}" ]]; then
			break
		else
			echo "Folder not found, try again."
		fi
	done

	echo "Enter destination location:
	1.Anime TV
	2.Anime Movies
	3.Light Novels
	4.Music
	5.Video
	x.Abort!"

	read dest_folder

	if [[ "$dest_folder" == "x" ]]; then
		echo "Terminate Code"
		exit 0
	fi

	dest_folder="${folders[${dest_folder}-1]}"

	while true; do
		echo "This will hardlink ${downloads_dir}/${folder_name} to ${dest_folder}, proceed?(y/n)"
		read confirmation
		if [[ "$confirmation" == "y" ]] || [[ "$confirmation" == "n" ]]; then
			break
		else
			echo "unknown answer."
		fi
	done

	if [[ "$confirmation" == "y" ]]; then
		cp -r -l "${downloads_dir}/${folder_name}" "$dest_folder"
		echo "Finished linking."
	else
		echo "Script does nothing ¯\_(ツ)_/¯"
	fi

	echo "Continue? (y/n)"
	read input
	if [[ "$input" == "n" ]]; then
		echo "Script done!"
		break
	else
		echo "continue.."
	fi
done